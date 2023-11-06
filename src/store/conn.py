from typing import AsyncContextManager, AsyncIterator, TypeAlias
from contextlib import asynccontextmanager

from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncConnection

from store import Store, StoreError

AsyncConenctionContext: TypeAlias = AsyncContextManager[AsyncConnection]


def _eng_is_init(store: Store) -> AsyncEngine:
    if store.db is None:
        raise StoreError("Database not initialized!", "no_db_init")
    else:
        return store.db


def _begin_conn(engine: AsyncEngine) -> AsyncConenctionContext:
    return engine.begin()


def _kv_is_init(store: Store) -> Redis:
    if store.kv is None:
        raise StoreError("Database not initialized!", "no_db_init")
    else:
        return store.kv


def get_kv(store: Store) -> Redis:
    return _kv_is_init(store)


@asynccontextmanager
async def get_conn(store: Store) -> AsyncIterator[AsyncConnection]:
    if store.session is None:
        # If there is no store session, just open a transaction as normally, inside a with block
        async with _begin_conn(_eng_is_init(store)) as conn:
            yield conn
    else:
        # In this case use the pre-existing connection, and at the end commit ("commit-as-you-go")
        try:
            yield store.session
        finally:
            await store.session.commit()


@asynccontextmanager
async def store_session(store: Store) -> AsyncIterator[Store]:
    """Use this to reuse a connection across multiple functions. Ensure it is only used within one request.
    Ensure that all consumers commit their own transactions."""
    # It opens a connection
    conn = await _eng_is_init(store).connect().start()
    store.session = conn
    try:
        # `yield` means that when this is called `with store_session(store) as session`, session is what comes after
        # `yield`
        yield store
    finally:
        # `finally` is called after the `with` block ends
        if store.session is None:
            raise StoreError("Session was set to None before closing!")
        await store.session.close()
        store.session = None
