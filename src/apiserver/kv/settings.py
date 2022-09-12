from pydantic import BaseModel
from apiserver.env import config, ConfigError, config_path


class KvAddress(BaseModel):
    host: str
    port: int
    db_n: int
    password: str


try:
    KV_HOST = config['KV_HOST']
    KV_PORT = config['KV_PORT']
    KV_PASSWORD = config['KV_PASS']
except KeyError as e:
    raise ConfigError(f"Not all mandatory config values set in {config_path.resolve()}!") from e

KV_ADDRESS = KvAddress(host=KV_HOST, port=KV_PORT, db_n=0, password=KV_PASSWORD)
