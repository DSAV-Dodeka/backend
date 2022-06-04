from pydantic import BaseModel
from dodekaserver.env import config


class KvAddress(BaseModel):
    host: str
    port: int
    db_n: int
    password: str


env_kv_host = config.get('KV_HOST')
env_kv_port = config.get('KV_PORT')
env_kv_pass = config.get('KV_PASS')

KV_HOST = env_kv_host if env_kv_port is not None else "localhost"
KV_PORT = env_kv_port if env_kv_port is not None else 6379
KV_PASSWORD = env_kv_pass if env_kv_pass is not None else "redisredis"
KV_ADDRESS = KvAddress(host=KV_HOST, port=KV_PORT, db_n=0, password=KV_PASSWORD)

