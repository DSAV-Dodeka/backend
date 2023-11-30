from typing import Any, Optional

import os
from pathlib import Path
import tomllib
from apiserver.app.error import AppEnvironmentError

from apiserver.resources import res_path, project_path
from store import StoreConfig


# Different scenarios:
# 1) Production ('production'): Every config value is loaded either from config files included in the Docker build or at
# runtime as environment variables (env.py), either set pre-deployment or set at deployment. In this case it can load in
# secrets.
# 2) Testing environment ('test'): Fully featured, automated testing environment in CI. Here it will not affect any
# deployment but can still test against as a live system. It can load in certain secrets, like e-mail passwords. Uses a
# dedicated config file for env.py.
# 3) Local (dev) environment ('localdev'): Can be set up fully featured. No automatic loading of secrets, but can be set
# locally. These secrets MUST NEVER be stored in Git. Use devenv.toml.local for this. Some tests with live side effects
# can be run.
# 4) No environment ('envless'): Can be in tests either locally or in automated CI, but not in a live environment. No
# access to any secrets and only dummy values from env.py. It does use define.py.


# See below for appropriate values for specific environments
class Config(StoreConfig):
    APISERVER_ENV: str

    # All 'envless' PASSWORDS MUST BE DUMMY

    # 'envless' MUST BE DUMMY
    # RECOMMENDED TO LOAD AS ENVIRON
    KEY_PASS: str

    MAIL_ENABLED: bool

    # 'envless' MUST BE DUMMY
    # RECOMMENDED TO LOAD AS ENVIRON
    MAIL_PASS: str

    SMTP_SERVER: str
    SMTP_PORT: int

    RECREATE: str = "no"

    DB_NAME_ADMIN: str


def get_config_path(config_path_name: Optional[os.PathLike[Any]] = None) -> Path:
    env_config_path = os.environ.get("APISERVER_CONFIG")
    if env_config_path is not None:
        return Path(env_config_path)
    elif config_path_name is not None:
        return Path(config_path_name)

    try_paths = [
        res_path.joinpath("env.toml"),
        project_path.joinpath("devenv.toml.local"),
        project_path.joinpath("devenv.toml"),
    ]

    for path in try_paths:
        if path.exists():
            return path

    raise AppEnvironmentError(
        "No env.toml found! If you are in development, did you remove `devenv.toml`? If"
        " you are in production, was `env.toml` not added to resources?"
    )


def load_config_with_message(
    config_path_name: Optional[os.PathLike[Any]] = None,
) -> tuple[Config, str]:
    config_path = get_config_path(config_path_name)

    with open(config_path, "rb") as f:
        config = tomllib.load(f)

    keys_in_environ = set(config.keys()).intersection(os.environ.keys())
    override_message = (
        f" with overriding environment variables: {keys_in_environ}"
        if keys_in_environ
        else ""
    )

    config |= os.environ  # override loaded values with environment variables

    config_message = f"config from {config_path}{override_message}"

    return Config.model_validate(config), config_message


def load_config(config_path_name: Optional[os.PathLike[Any]] = None) -> Config:
    config, _ = load_config_with_message(config_path_name)

    return config
