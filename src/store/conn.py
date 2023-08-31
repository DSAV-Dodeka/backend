from typing import AsyncIterator

from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncConnection

from store.store import Store, StoreError


def eng_is_init(store: Store):
    if store.db is None:
        raise StoreError("Database not initialized!", "no_db_init")
    else:
        return store.db


def begin_conn(engine: AsyncEngine) -> AsyncIterator[AsyncConnection]:
    return engine.begin()


def kv_is_init(store: Store) -> Redis:
    if store.kv is None:
        raise StoreError("Database not initialized!", "no_db_init")
    else:
        return store.kv
