from typing import Optional

import os
from pathlib import Path

import tomli
from pydantic import BaseModel

from apiserver import res_path


class ConfigError(Exception):
    pass


class Config(BaseModel):
    app_port: int = 4243
    issuer: str
    frontend_client_id: str
    backend_client_id: str

    valid_redirects: set[str]

    credentials_url: str

    DB_USER: str
    DB_PASS: str
    DB_HOST: str = "localhost"
    DB_PORT: str = 3141
    DB_NAME: str
    DB_NAME_ADMIN: str

    KV_HOST: str = "localhost"
    KV_PORT: str = 6379
    KV_PASS: str


def load_config(config_path_name: Optional[os.PathLike] = None) -> Config:
    env_config_path = os.environ.get("APISERVER_CONFIG")
    if env_config_path is not None:
        config_path = Path(env_config_path)
    elif config_path_name is None:
        config_path = res_path.joinpath("default.config.toml")
    else:
        config_path = Path(config_path_name)

    with open(config_path, "rb") as f:
        config_dict = tomli.load(f)

    # Config will contain all variables in a dict
    config = {
        **config_dict,
        **os.environ,  # override loaded values with environment variables
    }

    # try:
    #     kv_host = config['KV_HOST']
    #     kv_port = config['KV_PORT']
    #     kv_password = config['KV_PASS']
    # except KeyError as e:
    #     raise ConfigError(f"Not all mandatory config values set in {config_path.resolve()}!") from e

    return Config.parse_obj(config)
