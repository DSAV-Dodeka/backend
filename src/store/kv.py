from typing import Any, Optional, Union

from redis.asyncio import Redis
from redis.exceptions import ResponseError

__all__ = [
    "store_json",
    "get_json",
    "store_kv",
    "get_val_kv",
    "pop_json",
    "store_json_perm",
    "store_json_multi",
    "store_kv_perm",
    "pop_kv",
    "store_string",
    "get_string",
    "pop_string",
]

JsonType = Union[str, int, float, bool, None, dict[str, "JsonType"], list["JsonType"]]


async def store_json(kv: Redis, key: str, json, expire: int, path: str = "."):
    async with kv.pipeline() as pipe:
        pipe.json().set(key, path, json)
        pipe.expire(key, expire)
        await pipe.execute()


async def get_json(kv: Redis, key: str, path: str = ".") -> JsonType:
    """'.' is the root path. Getting nested objects is as simple as passing '.first.deep' to set the JSON object at the
    key 'deep' within the top-level 'first' JSON object."""
    try:
        return await kv.json().get(key, path)
    except ResponseError:
        # This means the path does not exist
        return None


async def store_json_perm(kv: Redis, key: str, json, path: str = "."):
    """'.' is the root path. Getting nested objects is as simple as passing '.first.deep' to set the JSON object at the
    key 'deep' within the top-level 'first' JSON object."""
    await kv.json().set(key, path, json)


async def store_json_multi(kv: Redis, jsons_to_store: dict[str, dict]):
    async with kv.pipeline() as pipe:
        for k, v in jsons_to_store.items():
            pipe.json().set(k, ".", v)
        await pipe.execute()


async def pop_json(kv: Redis, key: str) -> Optional[dict]:
    async with kv.pipeline() as pipe:
        pipe.json().get(key)
        pipe.json().delete(key)
        results: list[Any] = await pipe.execute()
    # returns a list with the result for each call
    # first is the get result, second equal to '1' if delete successful
    try:
        return results[0] if results[1] else None
    except IndexError:
        return None


async def store_kv(kv: Redis, key: str, value, expire: int):
    return await kv.set(key, value, ex=expire)


async def store_kv_perm(kv: Redis, key: str, value):
    return await kv.set(key, value)


async def get_val_kv(kv: Redis, key: str) -> Optional[bytes]:
    return await kv.get(key)


async def pop_kv(kv: Redis, key: str) -> Optional[bytes]:
    async with kv.pipeline() as pipe:
        pipe.get(key)
        pipe.delete(key)
        results: list[Any] = await pipe.execute()
    # returns a list with the result for each call
    # first is the get result, second equal to '1' if delete successful
    try:
        return results[0] if results[1] else None
    except IndexError:
        return None


async def store_string(kv: Redis, key: str, value: str, expire: int = 1000):
    if expire == -1:
        await store_kv_perm(kv, key, value)
    else:
        await store_kv(kv, key, value, expire)


def string_return(value: Optional[bytes]) -> Optional[str]:
    if value is None:
        return None
    try:
        return value.decode()
    except UnicodeEncodeError:
        raise KvError("Data is not of unicode string type.", "", "bad_str_encode")


async def pop_string(kv: Redis, key: str) -> str:
    value = await pop_kv(kv, key)
    return string_return(value)


async def get_string(kv: Redis, key: str) -> str:
    value = await get_val_kv(kv, key)
    return string_return(value)


class KvError(Exception):
    """Exception that represents special internal errors."""

    def __init__(
        self, err_desc: str, err_internal: str, debug_key: Optional[str] = None
    ):
        self.err_desc = err_desc
        self.err_internal = err_internal
        self.debug_key = debug_key