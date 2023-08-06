from typing import Optional

import redis
from redis.asyncio import Redis
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncEngine

from auth.data import DataSource
from auth.env import Config


class SourceError(ConnectionError):
    pass


class DataError(ValueError):
    key: str

    def __init__(self, message, key):
        self.message = message
        self.key = key


class NoDataError(DataError):
    pass


class StoreSource(DataSource):
    # db: Optional[AsyncEngine] = None
    kv: Optional[Redis] = None

    def init_objects(self, config: Config):
        # db_cluster = (
        #     f"{config.DB_USER}:{config.DB_PASS}@{config.DB_HOST}:{config.DB_PORT}"
        # )
        # db_url = f"{db_cluster}/{config.DB_NAME}"
        # # Connections are not actually established, it simply initializes the connection parameters
        self.kv = Redis(
            host=config.KV_HOST, port=config.KV_PORT, db=0, password=config.KV_PASS
        )
        # self.db: AsyncEngine = create_async_engine(f"postgresql+asyncpg://{db_url}")

    async def connect(self):
        try:
            # Redis requires no explicit call to connect, it simply connects the first time
            # a call is made to the database, so we test the connection by pinging
            await self.kv.ping()
        except redis.ConnectionError:
            raise SourceError(
                "Unable to ping Redis server! Please check if it is running."
            )
        # try:
        #     async with self.db.connect() as conn:
        #         _ = conn.info
        # except SQLAlchemyError:
        #     raise SourceError(
        #         "Unable to connect to DB with SQLAlchemy! Please check if it is"
        #         " running."
        #     )

    async def disconnect(self):
        await self.kv.close()

    async def startup(self):
        await self.connect()

    async def shutdown(self):
        await self.disconnect()
