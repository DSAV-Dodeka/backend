__all__ = ["Source", "get_kv", "get_conn"]

from contextlib import _AsyncGeneratorContextManager, asynccontextmanager
from typing import AsyncIterator, Self

from redis import Redis
from sqlalchemy.ext.asyncio import AsyncConnection

from apiserver.env import Config
from auth.core.model import KeyState as AuthKeyState
from store.conn import (
    AsyncConenctionContext,
    RedisClient,
    get_kv as st_get_kv,
    get_conn as st_get_conn,
    store_session,
)
from store import Store


class KeyState(AuthKeyState):
    current_symmetric: str = ""
    old_symmetric: str = ""
    current_signing: str = ""


class Source:
    store: Store
    config: Config
    key_state: KeyState

    def __init__(self) -> None:
        self.store = Store()
        self.key_state = KeyState()


def get_kv(dsrc: Source) -> RedisClient:
    return st_get_kv(dsrc.store)


def get_conn(dsrc: Source) -> AsyncConenctionContext:
    return st_get_conn(dsrc.store)


@asynccontextmanager
async def source_session(dsrc: Source) -> AsyncIterator[Source]:
    """Use this to reuse a connection across multiple functions. Ensure it is only used within one request.
    Ensure that all consumers commit their own transactions."""
    # It opens a connection
    manager = store_session(dsrc.store)
    get_store = manager.__aenter__
    store = await get_store()
    try:
        # Not necessary, but we are being explicit
        dsrc.store = store
        yield dsrc
    finally:
        close = manager.__aexit__
        await close(None, None, None)
