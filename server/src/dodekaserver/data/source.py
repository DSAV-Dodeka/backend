from databases import Database

from dodekaserver.db.settings import DB_URL

__all__ = ['Source', 'dsrc']


class Source:
    db: Database = None
    db_url: str

    def __init__(self):
        self.db_url = DB_URL

    def init(self):
        self.db = Database(self.db_url)

    async def connect(self):
        await self.db.connect()

    async def disconnect(self):
        await self.db.disconnect()


dsrc = Source()
dsrc.init()
