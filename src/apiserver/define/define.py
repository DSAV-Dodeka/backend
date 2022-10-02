import tomli

from jinja2 import Environment, FileSystemLoader, select_autoescape

from apiserver import res_path

__all__ = [
    "LOGGER_NAME",
    "id_exp",
    "access_exp",
    "refresh_exp",
    "grace_period",
    "allowed_envs",
    "issuer",
    "frontend_client_id",
    "backend_client_id",
    "valid_redirects",
    "credentials_url",
    "res_path",
    "template_env",
    "onboard_email",
    "smtp_port",
    "smtp_server",
    "loc_dict",
    "email_expiration",
    "signup_url",
    "api_root",
]

config_path = res_path.joinpath("define.toml")
loc_path = res_path.joinpath("loc.toml")

with open(config_path, "rb") as f:
    config = tomli.load(f)

with open(loc_path, "rb") as f:
    loc_dict = tomli.load(f)


# These are constants that are not variable enough to be set by the config file
LOGGER_NAME = "backend"

id_exp = 10 * 60 * 60  # 10 hours
# access_exp = 5
access_exp = 1 * 60 * 60  # 1 hour
refresh_exp = 30 * 24 * 60 * 60  # 1 month

# grace_period = 1
grace_period = 3 * 60  # 3 minutes in which it is still accepted

email_expiration = 15 * 60


class ConfigError(Exception):
    pass


template_env = Environment(
    loader=FileSystemLoader(res_path.joinpath("templates")),
    autoescape=select_autoescape(),
)

try:
    allowed_envs: set[str] = set(config["allowed_envs"])
    api_root: str = config["api_root"]
    issuer: str = config["issuer"]
    frontend_client_id: str = config["frontend_client_id"]
    backend_client_id: str = config["backend_client_id"]

    valid_redirects: set[str] = set(config["valid_redirects"])

    credentials_url: str = config["credentials_url"]

    signup_url: str = config["signup_url"]

    onboard_email: str = config["onboard_email"]

    smtp_server: str = config["smtp_server"]
    smtp_port: int = config["smtp_port"]
except KeyError as e:
    raise ConfigError(
        f"Not all mandatory config values set in {config_path.resolve()}!"
    ) from e
