from typing import Type

from databases import Database

from dodekaserver.db.settings import DB_URL
from dodekaserver.db import DatabaseOperations as Db

__all__ = ['Source', 'dsrc']


class Source:
    """ Abstraction layer between the API endpoints and the database layer. """

    db: Database = None
    db_url: str
    # Just store the class/type since we only use static methods
    ops: Type[Db]

    def __init__(self):
        self.db_url = DB_URL
        self.ops = Db

    def init(self):
        self.db = Database(self.db_url)

    async def connect(self):
        await self.db.connect()

    async def disconnect(self):
        await self.db.disconnect()


dsrc = Source()
dsrc.init()
