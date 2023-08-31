from typing import Optional

import redis
from pydantic import BaseModel
from redis.asyncio import Redis
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine


class StoreError(ConnectionError):
    pass


class StoreConfig(BaseModel):
    DB_USER: str
    DB_PASS: str
    DB_HOST: str
    DB_PORT: int
    DB_NAME: str

    KV_HOST: str
    KV_PORT: int
    # RECOMMENDED TO LOAD AS ENVIRON
    KV_PASS: str


class Store:
    db: Optional[AsyncEngine] = None
    kv: Optional[Redis] = None

    def init_objects(self, config: StoreConfig):
        db_cluster = (
            f"{config.DB_USER}:{config.DB_PASS}@{config.DB_HOST}:{config.DB_PORT}"
        )
        db_url = f"{db_cluster}/{config.DB_NAME}"
        # # Connections are not actually established, it simply initializes the connection parameters
        self.kv = Redis(
            host=config.KV_HOST, port=config.KV_PORT, db=0, password=config.KV_PASS
        )
        self.db: AsyncEngine = create_async_engine(f"postgresql+asyncpg://{db_url}")

    async def connect(self):
        try:
            # Redis requires no explicit call to connect, it simply connects the first time
            # a call is made to the database, so we test the connection by pinging
            await self.kv.ping()
        except redis.ConnectionError:
            raise StoreError(
                "Unable to ping Redis server! Please check if it is running."
            )
        try:
            async with self.db.connect() as conn:
                _ = conn.info
        except SQLAlchemyError:
            raise StoreError(
                "Unable to connect to DB with SQLAlchemy! Please check if it is"
                " running."
            )

    async def disconnect(self):
        await self.kv.close()

    async def startup(self):
        await self.connect()

    async def shutdown(self):
        await self.disconnect()
