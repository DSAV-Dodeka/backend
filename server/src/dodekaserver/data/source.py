from typing import Type

from databases import Database
from redis import Redis

from dodekaserver.db.settings import DB_URL
from dodekaserver.db import DatabaseOperations as Db
from dodekaserver.kv.settings import KvAddress, KV_ADDRESS

__all__ = ['Source', 'dsrc']


class Source:
    """ Abstraction layer between the API endpoints and the database layer. """

    db: Database = None
    db_url: str
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
        await self.db.connect()

    async def disconnect(self):
        await self.db.disconnect()


dsrc = Source()
dsrc.init()
