from typing import Optional

from apiserver.data import Source, NoDataError
from apiserver.data.trs import store_string, get_string


async def set_startup_lock(dsrc: Source, value="locked"):
    await store_string(dsrc, "startup_lock", value, 25)


async def startup_is_locked(dsrc: Source) -> Optional[bool]:
    try:
        lock = await get_string(dsrc, "startup_lock")
        return lock == "locked"
    except NoDataError:
        return None
