from typing import Optional

from apiserver.data import Source, get_kv
from store.error import NoDataError
from store.kv import store_string, get_string


async def set_startup_lock(dsrc: Source, value="locked"):
    await store_string(get_kv(dsrc), "startup_lock", value, 25)


async def startup_is_locked(dsrc: Source) -> Optional[bool]:
    try:
        lock = await get_string(get_kv(dsrc), "startup_lock")
        return lock == "locked"
    except NoDataError:
        return None
