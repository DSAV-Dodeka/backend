import os
from pathlib import Path
import tomli
from apiserver import res_path

# env_config_path = os.environ.get("APISERVER_CONFIG")
# env_config_in_resources = os.environ.get("APISERVER_CONFIG_IN_RES")
# if env_config_path is None:
#     config_path = res_path.joinpath("test.config.toml")
# elif not env_config_in_resources:
#     config_path = Path(env_config_path)
# else:
#     config_path = res_path.joinpath(env_config_in_resources)
#
# with open(config_path, "rb") as f:
#     config_dict = tomli.load(f)
#
# # Config will contain all variables in a dict
# config = {
#     **config_dict,
#     **os.environ,  # override loaded values with environment variables
# }

# These are constants that are not variable enough to be set by the config file
LOGGER_NAME = "backend"

id_exp = 10 * 60 * 60  # 10 hours
# access_exp = 5
access_exp = 1 * 60 * 60  # 1 hour
refresh_exp = 30 * 24 * 60 * 60  # 1 month

# grace_period = 1
grace_period = 3 * 60  # 3 minutes in which it is still accepted


# class ConfigError(Exception):
#     pass
#
#
# try:
#     app_port: int = config['app_port']
#
#     issuer: str = config['issuer']
#     frontend_client_id: str = config['frontend_client_id']
#     backend_client_id: str = config['backend_client_id']
#
#     valid_redirects: set[str] = set(config['valid_redirects'])
#
#     credentials_url: str = config['credentials_url']
# except KeyError as e:
#     raise ConfigError(f"Not all mandatory config values set in {config_path.resolve()}!") from e
