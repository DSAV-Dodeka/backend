from typing import Union

from redis import Redis
from redis.commands.json.path import Path


__all__ = ['store_json', 'get_json', 'store_kv', 'get_kv']


def store_json(kv: Redis, key: str, json, expire: int):
    with kv.pipeline() as pipe:
        pipe.json().set(key, Path.root_path(), json)
        pipe.expire(key, expire)
        pipe.execute()


def get_json(kv: Redis, key: str):
    return kv.json().get(key)


def store_kv(kv: Redis, key: str, value, expire: int):
    return kv.set(key, value, ex=expire)


def get_kv(kv: Redis, key: str):
    return kv.get(key)
