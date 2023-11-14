from loguru import logger
from asyncio import sleep
from datetime import date
from random import random

from sqlalchemy import create_engine

from apiserver.data.api.classifications import insert_classification
from apiserver.data.source import KeyState
from apiserver.env import Config
from apiserver.lib.model.entities import (
    JWKSet,
    User,
    UserData,
    JWKPublicEdDSA,
    JWKSymmetricA256GCM,
)
from auth.data.relational.opaque import insert_opaque_row
from auth.hazmat.structs import A256GCMKey
from apiserver.lib.hazmat import keys
from apiserver.lib.hazmat.keys import ed448_private_to_pem
from auth.hazmat.crypt_dict import encrypt_dict, decrypt_dict
from auth.hazmat.key_decode import aes_from_symmetric
from auth.core import util
from store import StoreError
from apiserver import data
from apiserver.data import Source
from schema.model import metadata as db_model
from apiserver.data.admin import drop_recreate_database
from store.error import DataError


async def startup(dsrc: Source, config: Config, recreate: bool = False) -> None:
    # Checks lock: returns True if it is the first lock since at least 25 seconds (lock expire time)
    is_first_process = await wait_for_lock_is_first(dsrc)
    logger.debug(f"Unlocked startup, first={is_first_process}")
    # Only recreates if it is also the first lock since at least 25 seconds (lock expire time)
    logger.debug(f"Startup with recreate={recreate and is_first_process}")

    # Set lock
    await data.trs.startup.set_startup_lock(dsrc)
    if is_first_process and recreate:
        logger.warning("Dropping and recreating...")
        drop_create_database(config)

    # Store startup (tests connection)
    await dsrc.store.startup()

    if is_first_process and recreate:
        logger.warning("Initial population...")
        await initial_population(dsrc, config)

    # Load keys
    logger.debug("Loading keys.")
    key_state = await load_keys(dsrc, config)
    dsrc.key_state = key_state

    # Release lock
    await data.trs.startup.set_startup_lock(dsrc, "not")


MAX_WAIT_INDEX = 15


async def wait_for_lock_is_first(dsrc: Source) -> bool:
    """We need this lock because in production we spawn multiple processes, which each startup separately. Returns
    true if it is the first lock since at least 25 seconds (lock expire time)."""
    # We sleep for a shor time to increase the distribution in startup times, hopefully reducing race conditions
    await sleep(random() + 0.1)
    was_locked = await data.trs.startup.startup_is_locked(dsrc)
    logger.debug(f"Checked for startup lock: {was_locked}")
    if was_locked is None:
        return True
    elif was_locked is False:
        return False
    i = 0
    while await data.trs.startup.startup_is_locked(dsrc):
        await sleep(1)
        i += 1
        if i > MAX_WAIT_INDEX:
            raise StoreError("Waited too long during startup!")
    return False


def drop_create_database(config: Config) -> None:
    db_cluster = f"{config.DB_USER}:{config.DB_PASS}@{config.DB_HOST}:{config.DB_PORT}"
    db_url = f"{db_cluster}/{config.DB_NAME}"
    admin_db_url = f"{db_cluster}/{config.DB_NAME_ADMIN}"

    admin_engine = create_engine(
        f"postgresql+psycopg://{admin_db_url}", isolation_level="AUTOCOMMIT"
    )
    drop_recreate_database(admin_engine, config.DB_NAME)

    sync_engine = create_engine(f"postgresql+psycopg://{db_url}")
    db_model.create_all(bind=sync_engine)
    logger.warning("Populated database.")
    del admin_engine
    del sync_engine


async def initial_population(dsrc: Source, config: Config) -> None:
    kid1, kid2, kid3 = (util.random_time_hash_hex(short=True) for _ in range(3))
    old_symmetric = keys.new_symmetric_key(kid1)
    new_symmetric = keys.new_symmetric_key(kid2)
    signing_key = keys.new_ed448_keypair(kid3)

    jwk_set = JWKSet(keys=[old_symmetric, new_symmetric, signing_key])

    # Key used to decrypt the keys stored in the database
    runtime_key = aes_from_symmetric(config.KEY_PASS)

    utc_now = util.utc_timestamp()

    reencrypted_key_set = encrypt_dict(runtime_key.private, jwk_set.model_dump())
    async with data.get_conn(dsrc) as conn:
        await data.key.insert_jwk(conn, reencrypted_key_set)
        await data.key.insert_key(conn, kid1, utc_now, "enc")
        await data.key.insert_key(conn, kid2, utc_now + 1, "enc")
        await data.key.insert_key(conn, kid3, utc_now, "sig")

        opaque_setup = keys.new_opaque_setup(0)
        await insert_opaque_row(conn, opaque_setup)

    fake_record_pass = f"{util.random_time_hash_hex()}{util.random_time_hash_hex()}"
    fake_pw_file = keys.gen_pw_file(
        opaque_setup.value, fake_record_pass, "1_fakerecord"
    )

    fake_user = User(
        id_name="fakerecord",
        email="fakerecord",
        password_file=fake_pw_file,
        scope="none",
    )
    admin_user = User(
        id=0,
        id_name="admin",
        email="admin",
        # This does not adhere to OPAQUE requirements, so you cannot actually login with this
        # We don't set the password file to something valid to prevent us forgetting to set a secure password
        password_file="admin",
        scope="member admin",
    )
    admin_userdata = UserData(
        user_id="0_admin",
        active=False,
        registerid="",
        firstname="admin",
        lastname="admin",
        callname="admin",
        email="admin",
        phone="admin",
        av40id=0,
        joined=date.today(),
        birthdate=date.today(),
        registered=True,
        showage=False,
    )

    async with data.get_conn(dsrc) as conn:
        await data.user.insert_user(conn, admin_user)
        await data.ud.insert_userdata(conn, admin_userdata)
        user_id = await data.user.insert_return_user_id(conn, fake_user)
        assert user_id == "1_fakerecord"

        await insert_classification(conn, "training")
        await insert_classification(conn, "points")


async def get_keystate(dsrc: Source) -> KeyState:
    """The KeyState object includes the key IDs (kids) of the currently used keys."""
    async with data.get_conn(dsrc) as conn:
        # We get the Key IDs (kid) of the newest keys and also previous symmetric key
        # These newest ones will be used for signing new tokens
        new_pem_kid = await data.key.get_newest_pem(conn)
        new_symmetric_kid, old_symmetric_kid = await data.key.get_newest_symmetric(conn)

    return KeyState(
        current_symmetric=new_symmetric_kid,
        old_symmetric=old_symmetric_kid,
        current_signing=f"{new_pem_kid}-pem-private",
    )


async def load_keys_from_jwk(dsrc: Source, config: Config) -> JWKSet:
    """Loads keys from the database's jwk table (JSON Web Key). These are stored in standard JWK format and then
    encrypted with the runtime key. After decrypting, it re-encrypts the keys and stores them again.
    """

    # Key used to decrypt the keys stored in the database
    runtime_key = aes_from_symmetric(config.KEY_PASS)
    async with data.get_conn(dsrc) as conn:
        encrypted_key_set = await data.key.get_jwk(conn)
        key_set_dict = decrypt_dict(runtime_key.private, encrypted_key_set)
        key_set = JWKSet.model_validate(key_set_dict)
        # We re-encrypt as is required when using AES encryption
        reencrypted_key_set = encrypt_dict(runtime_key.private, key_set_dict)
        await data.key.update_jwk(conn, reencrypted_key_set)

    return key_set


async def load_keys(dsrc: Source, config: Config) -> KeyState:
    key_set = await load_keys_from_jwk(dsrc, config)
    key_state = await get_keystate(dsrc)

    pem_keys = []
    pem_private_keys = []
    symmetric_keys = []
    public_keys = []
    for key in key_set.keys:
        if key.alg == "EdDSA":
            if key.d is None:
                raise DataError(
                    "Key private bytes not defined for EdDSA key!",
                    "eddsa_no_private_bytes",
                )
            key_private_bytes = util.dec_b64url(key.d)
            # PyJWT only accepts keys in PEM format, so we convert them from the raw format we store them in
            pem_key, pem_private_key = ed448_private_to_pem(key_private_bytes, key.kid)
            pem_keys.append(pem_key)
            pem_private_keys.append(pem_private_key)
            # The public keys we will store in raw format, we want to exclude the private key as we want to be able to
            # publish these keys
            # The 'x' are the public key bytes (as set by the JWK standard)
            public_key = JWKPublicEdDSA.model_validate(key.model_dump())
            public_keys.append(public_key)
        elif key.alg == "A256GCM":
            symmetric_key_jwk = JWKSymmetricA256GCM.model_validate(key.model_dump())
            symmetric_key = A256GCMKey(
                kid=symmetric_key_jwk.kid, symmetric=symmetric_key_jwk.k
            )
            symmetric_keys.append(symmetric_key)

    # In the future we can publish these keys
    public_jwk_set = JWKSet(keys=public_keys)

    # Store in KV for quick access
    await data.trs.key.store_pem_keys(dsrc, pem_keys, pem_private_keys)
    await data.trs.key.store_symmetric_keys(dsrc, symmetric_keys)
    # Currently, this is not actually used, but it could be used to publicize the public key
    await data.trs.key.store_jwks(dsrc, public_jwk_set)

    return key_state
