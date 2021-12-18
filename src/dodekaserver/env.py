import os
from dotenv import dotenv_values
from dodekaserver import res_path

config = {
    **dotenv_values(res_path.joinpath("conf/db/deploydb.env")),
    **dotenv_values(res_path.joinpath("conf/kv/deploykv.env")),
    **dotenv_values(res_path.joinpath("conf/dev/dev.env")),
    **os.environ,  # override loaded values with environment variables
}