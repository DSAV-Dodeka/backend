from typing import Any, Optional, Union

from redis.asyncio import Redis
from redis.exceptions import ResponseError

from store.store import StoreError

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


def ensure_dict(j: JsonType) -> dict[str, JsonType]:
    if isinstance(j, dict):
        return j

    raise StoreError("Expected dict!")


async def store_json(
    kv: Redis, key: str, json: JsonType, expire: int, path: str = "."
) -> None:
    async with kv.pipeline() as pipe:
        # Redis type support is not perfect
        pipe.json().set(key, path, json)  # type: ignore
        pipe.expire(key, expire)
        await pipe.execute()


async def get_json(kv: Redis, key: str, path: str = ".") -> JsonType:
    """'.' is the root path. Getting nested objects is as simple as passing '.first.deep' to set the JSON object at the
    key 'deep' within the top-level 'first' JSON object."""
    try:
        # Redis does not have proper async types yet
        res: JsonType = await kv.json().get(key, path)  # type: ignore
        return res
    except ResponseError:
        # This means the path does not exist
        return None


async def store_json_perm(
    kv: Redis, key: str, json: dict[str, Any], path: str = "."
) -> None:
    """'.' is the root path. Getting nested objects is as simple as passing '.first.deep' to set the JSON object at the
    key 'deep' within the top-level 'first' JSON object."""
    # Redis does not have proper async types yet
    await kv.json().set(key, path, json)  # type: ignore


async def store_json_multi(kv: Redis, jsons_to_store: dict[str, Any]) -> None:
    async with kv.pipeline() as pipe:
        for k, v in jsons_to_store.items():
            # Redis type support is not perfect
            pipe.json().set(k, ".", v)  # type: ignore
        await pipe.execute()


async def pop_json(kv: Redis, key: str) -> Optional[JsonType]:
    async with kv.pipeline() as pipe:
        # Redis type support is not perfect
        pipe.json().get(key)  # type: ignore
        pipe.json().delete(key)  # type: ignore
        results = await pipe.execute()
    # returns a list with the result for each call
    # first is the get result, second equal to '1' if delete successful
    try:
        get_result: JsonType = results[0] if results[1] == 1 else None
        return get_result
    except IndexError:
        return None


async def store_kv(kv: Redis, key: str, value: Any, expire: int) -> None:
    await kv.set(key, value, ex=expire)


async def store_kv_perm(kv: Redis, key: str, value: Any) -> None:
    await kv.set(key, value)


async def get_val_kv(kv: Redis, key: str) -> Optional[bytes]:
    # Redis type support is not perfect
    return await kv.get(key)  # type: ignore


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


async def store_string(kv: Redis, key: str, value: str, expire: int = 1000) -> None:
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


async def pop_string(kv: Redis, key: str) -> Optional[str]:
    value = await pop_kv(kv, key)
    return string_return(value)


async def get_string(kv: Redis, key: str) -> Optional[str]:
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
