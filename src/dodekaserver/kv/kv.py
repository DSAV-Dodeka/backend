from redis import Redis
from redis.commands.json.path import Path


__all__ = ['store_json', 'get_json']


def store_json(kv: Redis, key: str, json, expire: int):
    with kv.pipeline() as pipe:
        pipe.json().set(key, Path.rootPath(), json)
        pipe.expire(key, expire)
        pipe.execute()


def get_json(kv: Redis, key: str):
    return kv.json().get(key)
