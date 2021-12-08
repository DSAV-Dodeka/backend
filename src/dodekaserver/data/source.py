from typing import Type

import redis
from databases import Database
from redis import Redis

from dodekaserver.db.settings import DB_URL
from dodekaserver.db import DatabaseOperations as Db
from dodekaserver.kv.settings import KvAddress, KV_ADDRESS

__all__ = ['Source', 'dsrc']


class SourceError(ConnectionError):
    pass


class Source:
    """ Abstraction layer between the API endpoints and the database layer. """

    db: Database = None
    db_url: str
    kv_addr: KvAddress
    kv: Redis
    # Just store the class/type since we only use static methods
    ops: Type[Db]

    def __init__(self):
        self.db_url = DB_URL
        self.kv_addr = KV_ADDRESS
        self.ops = Db

    def init(self):
        self.db = Database(self.db_url)
        self.kv = Redis(host=self.kv_addr.host, port=self.kv_addr.port, db=self.kv_addr.db_n)

    async def connect(self):
        try:
            await self.db.connect()
        except redis.ConnectionError:
            raise SourceError(f"Unable to connect to DB! Please check if it is running.")
        try:
            self.kv.ping()
        except redis.ConnectionError:
            raise SourceError(f"Unable to ping Redis server! Please check if it is running.")

    async def disconnect(self):
        await self.db.disconnect()


dsrc = Source()
dsrc.init()
