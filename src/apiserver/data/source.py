from typing import Type, Optional
from dataclasses import dataclass

import redis
from databases import Database

from redis.asyncio import Redis
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import create_async_engine, AsyncEngine

from apiserver.auth.crypto_util import aes_from_symmetric, decrypt_dict, encrypt_dict
from apiserver.auth.key_util import ed448_private_to_pem
from apiserver.define.entities import JWKSet, JWK, A256GCMKey
from apiserver.env import Config
from apiserver.db.ops import DbOperations
from apiserver.db.use import PostgresOperations
import apiserver.data as data

__all__ = ['Source', 'DataError', 'Gateway', 'DbOperations', 'NoDataError']

from apiserver.utilities import dec_b64url


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
    db: Optional[Database] = None
    kv: Optional[Redis] = None
    # Just store the class/type since we only use static methods
    ops: Type['DbOperations']

    def __init__(self, ops: Type[DbOperations] = None):
        self.ops = PostgresOperations

    def init_objects(self, config: Config):
        db_cluster = f"{config.DB_USER}:{config.DB_PASS}@{config.DB_HOST}:{config.DB_PORT}"
        db_url = f"{db_cluster}/{config.DB_NAME}"
        # Connections are not actually established, it simply initializes the connection parameters
        self.db = Database(f"postgresql://{db_url}")
        self.kv = Redis(host=config.KV_HOST, port=config.KV_PORT, db=0,
                        password=config.KV_PASS)
        self.engine: AsyncEngine = create_async_engine(
            f"postgresql+asyncpg://{db_url}"
        )

    async def connect(self):
        try:
            await self.db.connect()
        except ConnectionError:
            raise SourceError(f"Unable to connect to DB! Please check if it is running.")
        try:
            # Redis requires no explicit call to connect, it simply connects the first time
            # a call is made to the database, so we test the connection by pinging
            await self.kv.ping()
        except redis.ConnectionError:
            raise SourceError(f"Unable to ping Redis server! Please check if it is running.")
        try:
            async with self.engine.connect() as conn:
                pass
        except DBAPIError:
            raise SourceError(f"Unable to connect to DB with SQLAlchemy! Please check if it is running.")

    async def disconnect(self):
        await self.db.disconnect()
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

    async def startup(self, config: Config):
        await self.gateway.startup()
        await load_keys(self, config)

    async def shutdown(self):
        await self.gateway.shutdown()


async def load_keys(dsrc: Source, config: Config):
    runtime_key = aes_from_symmetric(config.KEY_PASS)
    async with data.get_conn(dsrc) as conn:
        encrypted_key_set = await data.key.get_jwk(dsrc, conn)
        key_set_dict = decrypt_dict(runtime_key, encrypted_key_set)
        key_set: JWKSet = JWKSet.parse_obj(key_set_dict)
        reencrypted_key_set = encrypt_dict(runtime_key, key_set_dict)
        await data.key.update_jwk(dsrc, conn, reencrypted_key_set)
        new_pem_kid = await data.key.get_newest_pem(dsrc, conn)
        new_symmetric_kid, old_symmetric_kid = await data.key.get_newest_symmetric(dsrc, conn)

    pem_keys = []
    symmetric_keys = []
    public_keys = []
    for key in key_set.keys:
        if key.alg == "EdDSA":
            key_private_bytes = dec_b64url(key.d)
            pem_key = ed448_private_to_pem(key_private_bytes, key.kid)
            pem_keys.append(pem_key)
            public_key_dict: dict = key.copy(exclude={'d'}).dict()
            public_keys.append(public_key_dict)
        elif key.alg == "A256GCM":
            symmetric_key = A256GCMKey(kid=key.kid, symmetric=key.k)
            symmetric_keys.append(symmetric_key)

    public_jwk_set = JWKSet(keys=public_keys)

    await data.kv.store_pem_keys(dsrc, pem_keys)
    await data.kv.store_symmetric_keys(dsrc, symmetric_keys)
    await data.kv.store_jwks(dsrc, public_jwk_set)
    # We don't store these in the KV since that is an additional roundtrip that is not worth it
    # Consequently, they can only be refreshed at restart
    dsrc.state.current_pem = new_pem_kid
    dsrc.state.current_symmetric = new_symmetric_kid
    dsrc.state.old_symmetric = old_symmetric_kid
