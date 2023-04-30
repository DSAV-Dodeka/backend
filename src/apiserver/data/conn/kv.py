from redis.asyncio import Redis

from apiserver.data import Source, DataError


def kv_is_init(dsrc: Source) -> Redis:
    if dsrc.gateway.kv is None:
        raise DataError("Database not initialized!", "no_db_init")
    else:
        return dsrc.gateway.kv


def get_kv(dsrc: Source) -> Redis:
    return kv_is_init(dsrc)
