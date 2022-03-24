import os
from dotenv import dotenv_values
from dodekaserver import res_path

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
