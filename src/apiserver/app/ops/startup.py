import logging
from asyncio import sleep
from datetime import date
from random import random

from sqlalchemy import create_engine

from apiserver.env import Config
from apiserver.lib.model.entities import JWKSet, User, UserData, JWKPublicEdDSA
from auth.data.schemad.opaque import insert_opaque_row
from auth.hazmat.structs import A256GCMKey
from apiserver.lib.hazmat import keys
from apiserver.lib.hazmat.keys import ed448_private_to_pem
from auth.hazmat.crypt_dict import encrypt_dict, decrypt_dict
from auth.hazmat.key_decode import aes_from_symmetric
from auth.core import util
from store import StoreError
from apiserver.define import LOGGER_NAME
from apiserver import data
from apiserver.data import Source
from schema.model import metadata as db_model
from apiserver.data.admin import drop_recreate_database

logger = logging.getLogger(LOGGER_NAME)


async def startup(dsrc: Source, config: Config, recreate=False):
    # Checks lock: returns True if no lock had been in place, False otherwise
    first_lock = await waiting_lock(dsrc)
    logger.debug(f"{first_lock} - lock status")

    # Set lock
    await data.trs.startup.set_startup_lock(dsrc)
    if first_lock and recreate:
        logger.debug("Dropping and recreating...")
        drop_create_database(config)
    # Connect to store
    await dsrc.store.startup()

    if first_lock and recreate:
        await initial_population(dsrc, config)
    # Load keys
    await load_keys(dsrc, config)

    # Release lock
    await data.trs.startup.set_startup_lock(dsrc, "not")


MAX_WAIT_INDEX = 15


async def waiting_lock(dsrc: Source):
    """We need this lock because in production we spawn multiple processes, which each startup separately."""
    await sleep(random() + 0.1)
    was_locked = await data.trs.startup.startup_is_locked(dsrc)
    logger.debug(f"{was_locked} - was_locked init")
    i = 0
    while was_locked and await data.trs.startup.startup_is_locked(dsrc):
        was_locked = True
        await sleep(1)
        i += 1
        if i > MAX_WAIT_INDEX:
            raise StoreError("Waited too long during startup!")
    return was_locked is None


def drop_create_database(config: Config):
    # runtime_key = aes_from_symmetric(config.KEY_PASS)
    db_cluster = f"{config.DB_USER}:{config.DB_PASS}@{config.DB_HOST}:{config.DB_PORT}"
    db_url = f"{db_cluster}/{config.DB_NAME}"
    admin_db_url = f"{db_cluster}/{config.DB_NAME_ADMIN}"

    admin_engine = create_engine(
        f"postgresql://{admin_db_url}", isolation_level="AUTOCOMMIT"
    )
    drop_recreate_database(admin_engine, config.DB_NAME)

    sync_engine = create_engine(f"postgresql://{db_url}")
    db_model.metadata.create_all(bind=sync_engine)
    del admin_engine
    del sync_engine


async def initial_population(dsrc: Source, config: Config):
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


async def load_keys(dsrc: Source, config: Config):
    # Key used to decrypt the keys stored in the database
    runtime_key = aes_from_symmetric(config.KEY_PASS)
    async with data.get_conn(dsrc) as conn:
        encrypted_key_set = await data.key.get_jwk(conn)
        key_set_dict = decrypt_dict(runtime_key.private, encrypted_key_set)
        key_set: JWKSet = JWKSet.model_validate(key_set_dict)
        # We re-encrypt as is required when using AES encryption
        reencrypted_key_set = encrypt_dict(runtime_key.private, key_set_dict)
        await data.key.update_jwk(conn, reencrypted_key_set)
        # We get the Key IDs (kid) of the newest keys and also previous symmetric key
        # These newest ones will be used for signing new tokens
        new_pem_kid = await data.key.get_newest_pem(conn)
        new_symmetric_kid, old_symmetric_kid = await data.key.get_newest_symmetric(conn)

    pem_keys = []
    pem_private_keys = []
    symmetric_keys = []
    public_keys = []
    for key in key_set.keys:
        if key.alg == "EdDSA":
            key_private_bytes = util.dec_b64url(key.d)
            # PyJWT only accepts keys in PEM format, so we convert them from the raw format we store them in
            pem_key, pem_private_key = ed448_private_to_pem(key_private_bytes, key.kid)
            pem_keys.append(pem_key)
            pem_private_keys.append(pem_private_key)
            # The public keys we will store in raw format, we want to exclude the private key as we want to be able to
            # publish these keys
            # The 'x' are the public key bytes (as set by the JWK standard)
            public_key = JWKPublicEdDSA(
                alg=key.alg, kid=key.kid, kty=key.kty, use=key.use, crv=key.crv, x=key.x
            )
            public_keys.append(public_key)
        elif key.alg == "A256GCM":
            symmetric_key = A256GCMKey(kid=key.kid, symmetric=key.k)
            symmetric_keys.append(symmetric_key)

    # In the future we can publish these keys
    public_jwk_set = JWKSet(keys=public_keys)

    # Store in KV for quick access
    await data.trs.key.store_pem_keys(dsrc, pem_keys, pem_private_keys)
    await data.trs.key.store_symmetric_keys(dsrc, symmetric_keys)
    # Currently, this is not actually used, but it could be used to publicize the public key
    await data.trs.key.store_jwks(dsrc, public_jwk_set)
    # We don't store these in the KV since that is an additional roundtrip that is not worth it
    # Consequently, they can only be refreshed at restart
    dsrc.key_state.current_signing = f"{new_pem_kid}-pem-private"
    dsrc.key_state.current_symmetric = new_symmetric_kid
    dsrc.key_state.old_symmetric = old_symmetric_kid