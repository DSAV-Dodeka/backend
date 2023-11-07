from typing import Optional
from store.kv import (
    store_string as st_store_string,
    pop_string as st_pop_string,
    get_string as st_get_string,
)
from apiserver.data import Source, get_kv


async def store_string(dsrc: Source, key: str, value: str, expire: int = 1000) -> None:
    await st_store_string(get_kv(dsrc), key, value, expire)


async def pop_string(dsrc: Source, key: str) -> Optional[str]:
    return await st_pop_string(get_kv(dsrc), key)


async def get_string(dsrc: Source, key: str) -> Optional[str]:
    return await st_get_string(get_kv(dsrc), key)
