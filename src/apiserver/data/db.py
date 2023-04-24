from typing import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine

from apiserver.data import Source, DataError


def eng_is_init(dsrc: Source):
    if dsrc.gateway.db is None:
        raise DataError("Database not initialized!", "no_db_init")
    else:
        return dsrc.gateway.db


def begin_conn(engine: AsyncEngine) -> AsyncIterator[AsyncConnection]:
    return engine.begin()


def get_conn(dsrc: Source) -> AsyncIterator[AsyncConnection]:
    return begin_conn(eng_is_init(dsrc))
