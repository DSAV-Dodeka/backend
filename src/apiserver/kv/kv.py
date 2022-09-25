from typing import Any, Optional

from redis.asyncio import Redis
# from redis import Redis
from redis.commands.json.path import Path


__all__ = ['store_json', 'get_json', 'store_kv', 'get_kv', 'pop_json']


async def store_json(kv: Redis, key: str, json, expire: int):
    async with kv.pipeline() as pipe:
        pipe.json().set(key, Path.root_path(), json)
        pipe.expire(key, expire)
        await pipe.execute()


async def get_json(kv: Redis, key: str) -> Optional[dict]:
    return await kv.json().get(key)


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


async def get_kv(kv: Redis, key: str) -> Optional[bytes]:
    return await kv.get(key)
