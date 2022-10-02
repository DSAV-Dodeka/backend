import logging
from typing import Type, Optional
from dataclasses import dataclass

from random import random
from anyio import sleep
import redis
from redis.asyncio import Redis
from sqlalchemy import create_engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import create_async_engine, AsyncEngine

from apiserver.define import LOGGER_NAME
from apiserver.define.entities import JWKSet, A256GCMKey, User
import apiserver.utilities as util
from apiserver.utilities.crypto import aes_from_symmetric, decrypt_dict, encrypt_dict
from apiserver.utilities.keys import ed448_private_to_pem
import apiserver.db.model as db_model
from apiserver.db.admin import drop_recreate_database
from apiserver.db.ops import DbOperations
from apiserver.db.use import PostgresOperations
from apiserver.env import Config
import apiserver.data as data

__all__ = ["Source", "DataError", "Gateway", "DbOperations", "NoDataError"]


logger = logging.getLogger(LOGGER_NAME)


class SourceError(ConnectionError):
    pass


class DataError(ValueError):
    key: str

    def __init__(self, message, key):
        self.message = message
        self.key = key


class NoDataError(DataError):
    pass


class Gateway:
    engine: Optional[AsyncEngine] = None
    kv: Optional[Redis] = None
    # Just store the class/type since we only use static methods
    ops: Type["DbOperations"]

    def __init__(self, ops: Type[DbOperations] = None):
        self.ops = PostgresOperations

    def init_objects(self, config: Config):
        db_cluster = (
            f"{config.DB_USER}:{config.DB_PASS}@{config.DB_HOST}:{config.DB_PORT}"
        )
        db_url = f"{db_cluster}/{config.DB_NAME}"
        # Connections are not actually established, it simply initializes the connection parameters
        self.kv = Redis(
            host=config.KV_HOST, port=config.KV_PORT, db=0, password=config.KV_PASS
        )
        self.engine: AsyncEngine = create_async_engine(f"postgresql+asyncpg://{db_url}")

    async def connect(self):
        try:
            # Redis requires no explicit call to connect, it simply connects the first time
            # a call is made to the database, so we test the connection by pinging
            await self.kv.ping()
        except redis.ConnectionError:
            raise SourceError(
                f"Unable to ping Redis server! Please check if it is running."
            )
        try:
            async with self.engine.connect() as conn:
                _ = conn.info
        except SQLAlchemyError:
            raise SourceError(
                f"Unable to connect to DB with SQLAlchemy! Please check if it is"
                f" running."
            )

    async def disconnect(self):
        await self.kv.close()

    async def startup(self):
        await self.connect()

    async def shutdown(self):
        await self.disconnect()


@dataclass
class SourceState:
    current_pem: str = ""
    current_symmetric: str = ""


class Source:
    gateway: Gateway
    state: SourceState

    def __init__(self):
        self.gateway = Gateway()
        self.state = SourceState()

    def init_gateway(self, config: Config):
        self.gateway.init_objects(config)

    async def startup(self, config: Config, recreate=False):
        # Checks lock: returns True if no lock had been in place, False otherwise
        first_lock = await waiting_lock(self)
        logger.debug(f"{first_lock} - lock status")
        # Set lock
        await data.kv.set_startup_lock(self)
        if first_lock and recreate:
            drop_create_database(config)
        await self.gateway.startup()
        if first_lock and recreate:
            await initial_population(self, config)
        await load_keys(self, config)
        # Release lock
        await data.kv.set_startup_lock(self, "not")

    async def shutdown(self):
        await self.gateway.shutdown()


async def waiting_lock(dsrc: Source):
    await sleep(random() + 0.1)
    was_locked = await data.kv.startup_is_locked(dsrc)
    logger.debug(f"{was_locked} - was_locked init")
    i = 0
    while was_locked and await data.kv.startup_is_locked(dsrc):
        was_locked = True
        await sleep(1)
        i += 1
        if i > 15:
            raise SourceError(f"Waited too long during startup!")
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
    old_symmetric = util.keys.new_symmetric_key(kid1)
    new_symmetric = util.keys.new_symmetric_key(kid2)
    signing_key = util.keys.new_ed448_keypair(kid3)

    jwk_set = JWKSet(keys=[old_symmetric, new_symmetric, signing_key])

    # Key used to decrypt the keys stored in the database
    runtime_key = aes_from_symmetric(config.KEY_PASS)

    utc_now = util.utc_timestamp()

    reencrypted_key_set = encrypt_dict(runtime_key, jwk_set.dict())
    async with data.get_conn(dsrc) as conn:
        await data.key.insert_jwk(dsrc, conn, reencrypted_key_set)
        await data.key.insert_key(dsrc, conn, kid1, utc_now, "enc")
        await data.key.insert_key(dsrc, conn, kid2, utc_now + 1, "enc")
        await data.key.insert_key(dsrc, conn, kid3, utc_now, "sig")

        opaque_setup = util.keys.new_opaque_setup(0)
        await data.opaquesetup.insert_opaque_row(dsrc, conn, opaque_setup)

    fake_record_pass = f"{util.random_time_hash_hex()}{util.random_time_hash_hex()}"
    fake_pw_file = util.keys.gen_pw_file(
        opaque_setup.value, fake_record_pass, "1_fakerecord"
    )

    async with data.get_conn(dsrc) as conn:
        fake_user = User(
            id_name="fakerecord",
            email="fakerecord",
            password_file=fake_pw_file,
            scope="none",
        )
        user_id = await data.user.insert_return_user_id(dsrc, conn, fake_user)
        assert user_id == "1_fakerecord"


async def load_keys(dsrc: Source, config: Config):
    # Key used to decrypt the keys stored in the database
    runtime_key = aes_from_symmetric(config.KEY_PASS)
    async with data.get_conn(dsrc) as conn:
        encrypted_key_set = await data.key.get_jwk(dsrc, conn)
        key_set_dict = decrypt_dict(runtime_key, encrypted_key_set)
        key_set: JWKSet = JWKSet.parse_obj(key_set_dict)
        # We re-encrypt as is required when using AES encryption
        reencrypted_key_set = encrypt_dict(runtime_key, key_set_dict)
        await data.key.update_jwk(dsrc, conn, reencrypted_key_set)
        # We get the Key IDs (kid) of the newest keys and also previous symmetric key
        # These newest ones will be used for signing new tokens
        new_pem_kid = await data.key.get_newest_pem(dsrc, conn)
        new_symmetric_kid, old_symmetric_kid = await data.key.get_newest_symmetric(
            dsrc, conn
        )

    pem_keys = []
    symmetric_keys = []
    public_keys = []
    for key in key_set.keys:
        if key.alg == "EdDSA":
            key_private_bytes = util.dec_b64url(key.d)
            # PyJWT only accepts keys in PEM format, so we convert them from the raw format we store them in
            pem_key = ed448_private_to_pem(key_private_bytes, key.kid)
            pem_keys.append(pem_key)
            # The public keys we will store in raw format, we want to exclude the private key as we want to be able to
            # publish these keys
            public_key_dict: dict = key.copy(exclude={"d"}).dict()
            public_keys.append(public_key_dict)
        elif key.alg == "A256GCM":
            symmetric_key = A256GCMKey(kid=key.kid, symmetric=key.k)
            symmetric_keys.append(symmetric_key)

    # In the future we can publish these keys
    public_jwk_set = JWKSet(keys=public_keys)

    # Store in KV for quick access
    await data.kv.store_pem_keys(dsrc, pem_keys)
    await data.kv.store_symmetric_keys(dsrc, symmetric_keys)
    await data.kv.store_jwks(dsrc, public_jwk_set)
    # We don't store these in the KV since that is an additional roundtrip that is not worth it
    # Consequently, they can only be refreshed at restart
    dsrc.state.current_pem = new_pem_kid
    dsrc.state.current_symmetric = new_symmetric_kid
    dsrc.state.old_symmetric = old_symmetric_kid
