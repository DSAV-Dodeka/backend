import os
from dotenv import dotenv_values
from apiserver import res_path

# These config values are automatically moved to resources by a script
# These are sourced from the DSAV/dodeka repository
# Config will contain all environment variables in a dict
config = {
    **dotenv_values(res_path.joinpath("conf/db/deploydb.env")),
    **dotenv_values(res_path.joinpath("conf/kv/deploykv.env")),
    **dotenv_values(res_path.joinpath("conf/dev/dev.env")),
    **os.environ,  # override loaded values with environment variables
}

# These are constants that are not variable enough to be set by the config file
LOGGER_NAME = "backend"

id_exp = 10 * 60 * 60  # 10 hours
# access_exp = 5
access_exp = 1 * 60 * 60  # 1 hour
refresh_exp = 30 * 24 * 60 * 60  # 1 month

# grace_period = 1
grace_period = 3 * 60   # 3 minutes in which it is still accepted

issuer = "https://dsavdodeka.nl/auth"
frontend_client_id = "dodekaweb_client"
backend_client_id = "dodekabackend_client"

valid_redirects = {"http://localhost:3000/auth/callback", "https://dsavdodeka.nl/auth/callback"}

credentials_url = "http://localhost:4243/credentials/index.html"
