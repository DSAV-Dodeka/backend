from typing import Optional

import os
from pathlib import Path

import tomli
from pydantic import BaseModel

from apiserver import res_path


class ConfigError(Exception):
    pass


# Different scenarios:
# 1) Production ('production'): Every config value is loaded either from config files included in the Docker build or at
# runtime as environment variables (env.py), either set pre-deployment or set at deployment. In this case it can load in
# secrets.
# 2) Testing environment ('test'): Fully featured, automated testing environment in CI. Here it will not affect any
# deployment but can still test against as a live system. It can load in certain secrets, like e-mail passwords. Uses a
# dedicated config file for env.py.
# 3) Local (dev) environment ('localdev'): Can be set up fully featured. No automatic loading of secrets, but can be set
# locally. These secrets MUST NEVER be stored in Git. Use localenv.toml for this. Some tests with live side effects can
# be run.
# 4) No environment ('envless'): Can be in tests either locally or in automated CI, but not in a live environment. No
# access to any secrets and only dummy values from env.py. It does use define.py.

# See below for appropriate values for specific environments
class Config(BaseModel):
    APISERVER_ENV: str

    DB_USER: str
    # 'envless' MUST BE DUMMY
    # RECOMMENDED TO LOAD AS ENVIRON
    DB_PASS: str
    DB_HOST: str
    DB_PORT: str
    DB_NAME: str
    DB_NAME_ADMIN: str

    KV_HOST: str
    KV_PORT: str
    # 'envless' MUST BE DUMMY
    # RECOMMENDED TO LOAD AS ENVIRON
    KV_PASS: str

    # 'envless' MUST BE DUMMY
    # RECOMMENDED TO LOAD AS ENVIRON
    KEY_PASS: str

    # 'envless' MUST BE DUMMY
    # RECOMMENDED TO LOAD AS ENVIRON
    MAIL_PASS: str

    RECREATE: str = "no"


def load_config(config_path_name: Optional[os.PathLike] = None) -> Config:
    env_config_path = os.environ.get("APISERVER_CONFIG")
    if env_config_path is not None:
        config_path = Path(env_config_path)
    elif config_path_name is None:
        config_path = res_path.joinpath("env.toml")
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
