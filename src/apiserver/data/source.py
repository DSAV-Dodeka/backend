from dataclasses import dataclass

__all__ = ["Source", "DataError", "NoDataError", "get_kv", "get_conn"]

from typing import AsyncIterator

from redis import Redis
from sqlalchemy.ext.asyncio import AsyncConnection

from apiserver.env import Config
from store.conn import get_kv as st_get_kv, get_conn as st_get_conn
from store import Store


class DataError(ValueError):
    key: str

    def __init__(self, message, key):
        self.message = message
        self.key = key


class NoDataError(DataError):
    pass


@dataclass
class SourceState:
    current_pem: str = ""
    current_symmetric: str = ""


class Source:
    store: Store
    config: Config
    state: SourceState

    def __init__(self):
        self.store = Store()
        self.state = SourceState()


def get_kv(dsrc: Source) -> Redis:
    return st_get_kv(dsrc.store)


def get_conn(dsrc: Source) -> AsyncIterator[AsyncConnection]:
    return st_get_conn(dsrc.store)
