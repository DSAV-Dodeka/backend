import tomli
from apiserver import res_path

__all__ = ['LOGGER_NAME', 'id_exp', 'access_exp', 'refresh_exp', 'grace_period', 'environment', 'issuer',
           'frontend_client_id', 'backend_client_id', 'valid_redirects', 'credentials_url', 'res_path']

config_path = res_path.joinpath("define.toml")

with open(config_path, "rb") as f:
    config = tomli.load(f)


# These are constants that are not variable enough to be set by the config file
LOGGER_NAME = "backend"

id_exp = 10 * 60 * 60  # 10 hours
# access_exp = 5
access_exp = 1 * 60 * 60  # 1 hour
refresh_exp = 30 * 24 * 60 * 60  # 1 month

# grace_period = 1
grace_period = 3 * 60  # 3 minutes in which it is still accepted


class ConfigError(Exception):
    pass


try:
    environment: str = config['environment']

    issuer: str = config['issuer']
    frontend_client_id: str = config['frontend_client_id']
    backend_client_id: str = config['backend_client_id']

    valid_redirects: set[str] = set(config['valid_redirects'])

    credentials_url: str = config['credentials_url']
except KeyError as e:
    raise ConfigError(f"Not all mandatory config values set in {config_path.resolve()}!") from e
