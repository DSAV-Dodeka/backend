from redis.asyncio import Redis
# from redis import Redis
from redis.commands.json.path import Path


__all__ = ['store_json', 'get_json', 'store_kv', 'get_kv']


async def store_json(kv: Redis, key: str, json, expire: int):
    async with kv.pipeline() as pipe:
        pipe.json().set(key, Path.root_path(), json)
        pipe.expire(key, expire)
        await pipe.execute()


async def get_json(kv: Redis, key: str):
    return await kv.json().get(key)


async def store_kv(kv: Redis, key: str, value, expire: int):
    return await kv.set(key, value, ex=expire)


async def get_kv(kv: Redis, key: str):
    return await kv.get(key)
