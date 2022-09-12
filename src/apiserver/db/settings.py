from apiserver.env import config, ConfigError, config_path

try:
    DB_USERNAME = config['DB_USER']
    DB_PASSWORD = config['DB_PASS']

    # These can also be set for GitHub actions
    DB_HOST = config['DB_HOST']
    DB_PORT = config['DB_PORT']
    DB_NAME = config['DB_NAME']
    ADMIN_DB_NAME = config['DB_NAME_ADMIN']
except KeyError as e:
    raise ConfigError(f"Not all mandatory config values set in {config_path.resolve()}!") from e

DB_CLUSTER = f"postgresql://{DB_USERNAME}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}"
DB_URL = f"{DB_CLUSTER}/{DB_NAME}"
