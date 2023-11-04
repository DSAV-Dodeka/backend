__all__ = ["Source", "get_kv", "get_conn"]

from typing import AsyncIterator

from redis import Redis
from sqlalchemy.ext.asyncio import AsyncConnection

from apiserver.env import Config
from auth.core.model import KeyState as AuthKeyState
from store.conn import get_kv as st_get_kv, get_conn as st_get_conn, store_session
from store import Store


class KeyState(AuthKeyState):
    current_symmetric: str = ""
    old_symmetric: str = ""
    current_signing: str = ""


class Source:
    store: Store
    config: Config
    key_state: KeyState

    def __init__(self):
        self.store = Store()
        self.key_state = KeyState()


def get_kv(dsrc: Source) -> Redis:
    return st_get_kv(dsrc.store)


def get_conn(dsrc: Source) -> AsyncIterator[AsyncConnection]:
    return st_get_conn(dsrc.store)


def source_session(dsrc: Source) -> AsyncIterator[Source]:
    """Use this if you want to re-use a connection across multiple calls to a frame/context. Note: this does not create
    a single transaction. Those must be committed by consumers."""
    return store_session(dsrc.store)
