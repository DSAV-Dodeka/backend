import abc
from typing import Type
from abc import ABC

import redis
from databases import Database
from redis import Redis

# These settings modules contain top-level logic that loads all configuration variables
from dodekaserver.db.settings import DB_URL
from dodekaserver.kv.settings import KvAddress, KV_ADDRESS

from dodekaserver.db import DatabaseOperations as Db

__all__ = ['Source', 'dsrc', 'DataError', 'Gateway']


class SourceError(ConnectionError):
    pass


class DataError(ValueError):
    key: str

    def __init__(self, message, key):
        self.message = message
        self.key = key


class Gateway:
    db: Database = None
    db_url: str
    kv_addr: KvAddress
    kv: Redis = None
    # Just store the class/type since we only use static methods
    ops: Type[Db]

    def __init__(self, do_init: bool = True):
        self.db_url = DB_URL
        self.kv_addr = KV_ADDRESS
        self.ops = Db
        if do_init:
            self.init_objects()

    def init_objects(self):
        # Connections are not actually established, it simply initializes the connection parameters
        self.db = Database(self.db_url)
        self.kv = Redis(host=self.kv_addr.host, port=self.kv_addr.port, db=self.kv_addr.db_n)

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

    async def disconnect(self):
        await self.db.disconnect()

    async def startup(self):
        await self.connect()

    async def shutdown(self):
        await self.disconnect()


class Source:
    gateway: Gateway = Gateway()

    async def startup(self):
        await self.gateway.startup()

    async def shutdown(self):
        await self.gateway.shutdown()


dsrc = Source()
