import os

DB_USERNAME = "dodeka"
# //TODO load SECRET
DB_PASSWORD = "dodeka"

# These can also be set for GitHub actions
env_db_host = os.environ.get('DODEKA_DB_HOST')
env_db_port = os.environ.get('DODEKA_DB_PORT')

DB_HOST = env_db_host if env_db_host is not None else "localhost"
DB_PORT = env_db_port if env_db_host is not None else "3141"
DB_NAME = "dodeka"
ADMIN_DB_NAME = "postgres"

DB_CLUSTER = f"postgresql://{DB_USERNAME}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}"
DB_URL = f"{DB_CLUSTER}/{DB_NAME}"
