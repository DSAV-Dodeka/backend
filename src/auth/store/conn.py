from typing import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine
from redis.asyncio import Redis

from auth.store.source import StoreSource, DataError

# def eng_is_init(dsrc: StoreSource):
#     if dsrc.db is None:
#         raise DataError("Database not initialized!", "no_db_init")
#     else:
#         return dsrc.db
#
#
# def begin_conn(engine: AsyncEngine) -> AsyncIterator[AsyncConnection]:
#     return engine.begin()
#
#
# def get_conn(dsrc: StoreSource) -> AsyncIterator[AsyncConnection]:
#     return begin_conn(eng_is_init(dsrc))


def kv_is_init(dsrc: StoreSource) -> Redis:
    if dsrc.kv is None:
        raise DataError("Database not initialized!", "no_db_init")
    else:
        return dsrc.kv


def get_kv(dsrc: StoreSource) -> Redis:
    return kv_is_init(dsrc)
