from typing import Optional

from apiserver.data import Source, get_kv
from store.kv import store_string, get_string


async def set_startup_lock(dsrc: Source, value: str = "locked") -> None:
    await store_string(get_kv(dsrc), "startup_lock", value, 25)


async def startup_is_locked(dsrc: Source) -> Optional[bool]:
    """Returns None if it did not exist (so it is the first), True if it is locked, False if it is not locked but was
    previously locked."""

    lock = await get_string(get_kv(dsrc), "startup_lock")

    if lock is not None:
        return lock == "locked"

    return None
