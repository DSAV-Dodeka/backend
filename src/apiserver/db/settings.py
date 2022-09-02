from apiserver.env import config


env_db_user = config.get('DB_USER')
env_db_pass = config.get('DB_PASS')

# These can also be set for GitHub actions
env_db_host = config.get('DB_HOST')
env_db_port = config.get('DB_PORT')
env_db_name = config.get('DB_NAME')
env_admin_db_name = config.get('DB_NAME_ADMIN')

DB_USERNAME = env_db_user if env_db_user is not None else "dodeka"
DB_HOST = env_db_host if env_db_host is not None else "localhost"
DB_PORT = env_db_port if env_db_host is not None else "3141"
DB_PASSWORD = env_db_pass if env_db_pass is not None else "postpost"
DB_NAME = env_db_name if env_db_name is not None else "dodeka"
ADMIN_DB_NAME = env_admin_db_name if env_admin_db_name is not None else "postgres"

DB_CLUSTER = f"postgresql://{DB_USERNAME}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}"
DB_URL = f"{DB_CLUSTER}/{DB_NAME}"
