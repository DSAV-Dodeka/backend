from typing import Type, Optional

import redis
from databases import Database
from redis.asyncio import Redis
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import create_async_engine, AsyncEngine

from apiserver.auth.crypto_util import aes_from_symmetric
from apiserver.env import Config
from apiserver.db.ops import DbOperations
from apiserver.db.use import PostgresOperations

__all__ = ['Source', 'DataError', 'Gateway', 'DbOperations', 'NoDataError']


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


class Source:
    gateway: Gateway

    def __init__(self):
        self.gateway = Gateway()

    def init_gateway(self, config: Config):
        self.gateway.init_objects(config)

    async def startup(self, config: Config):
        await self.gateway.startup()
        await load_keys(self, config)

    async def shutdown(self):
        await self.gateway.shutdown()


async def load_keys(dsrc: Source, config: Config):
    aesgcm = aes_from_symmetric(config.KEY_PASS)

    # load from data the json, decrypt it, put it in the KV in the correct format, etc.