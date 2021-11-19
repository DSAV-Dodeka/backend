import os

DB_USERNAME = "dodeka"
DB_PASSWORD = "dodeka"
env_db_host = os.environ.get('DODEKA_DB_HOST')
DB_HOST = env_db_host if env_db_host is not None else "localhost"
env_db_port = os.environ.get('DODEKA_DB_PORT')
DB_PORT = env_db_port if env_db_host is not None else "3141"
DB_NAME = "dodeka"

DB_URL = f"postgresql://{DB_USERNAME}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
