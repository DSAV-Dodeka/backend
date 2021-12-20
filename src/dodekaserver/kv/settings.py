from pydantic import BaseModel
from dodekaserver.env import config


class KvAddress(BaseModel):
    host: str
    port: int
    db_n: int


env_kv_host = config.get('KV_HOST')
env_kv_port = config.get('KV_PORT')

KV_HOST = env_kv_host if env_kv_port is not None else "localhost"
KV_PORT = env_kv_port if env_kv_port is not None else 6379
KV_ADDRESS = KvAddress(host=KV_HOST, port=KV_PORT, db_n=0)
