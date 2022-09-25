import logging
from logging import Logger

import uvicorn

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.routing import Mount
from fastapi.exceptions import RequestValidationError

# We rely upon database parameters being set at import time, which is fragile, but the only way to easily re-use it
# in the app state
# In most cases this is where all environment variables and other configuration is loaded

from apiserver.define import res_path, ErrorResponse, error_response_handler, LOGGER_NAME, allowed_envs, \
    error_response_return
from apiserver.env import load_config, Config
# Import types separately to make it clear in what line the module is first loaded and its top-level run
from apiserver.data import Source

# Router modules, each router has its own API endpoints
import apiserver.routers.basic as basic
import apiserver.routers.auth as auth
import apiserver.routers.profile as profile
import apiserver.routers.onboard as onboard
import apiserver.routers.update as update


def init_logging(logger_name: str, log_level: int):
    logger_init = logging.getLogger(logger_name)
    logger_init.setLevel(log_level)
    handler = logging.StreamHandler()
    log_format = "%(levelprefix)s %(asctime)s | %(message)s"
    formatter = uvicorn.logging.DefaultFormatter(log_format, datefmt="%Y-%m-%d %H:%M:%S")
    handler.setFormatter(formatter)
    logger_init.addHandler(handler)
    return logger_init


def create_app() -> tuple[FastAPI, Logger]:
    # TODO change all origins
    origins = [
        "*",
    ]
    routes = [
        Mount('/credentials', app=StaticFiles(directory=res_path.joinpath("static/credentials"), html=True),
              name="credentials")
    ]
    new_app = FastAPI(routes=routes)
    new_app.include_router(basic.router)
    new_app.include_router(auth.router)
    new_app.include_router(profile.router)
    new_app.include_router(onboard.router)
    new_app.include_router(update.router)
    new_app.add_middleware(CORSMiddleware, allow_origins=origins, allow_methods=['*'],
                           allow_headers=['Authorization'])
    new_app.add_exception_handler(ErrorResponse, handler=error_response_handler)
    # TODO change logger behavior in tests
    new_logger = init_logging(LOGGER_NAME, logging.DEBUG)
    new_logger.info("Starting...")

    dsrc = Source()
    new_app.state.dsrc = dsrc

    return new_app, new_logger


# Running FastAPI relies on the fact the app is created at module top-level
# Seperating the logic in a function also allows it to be called elsewhere, like tests
app, logger = create_app()


# Should always be manually run in tests
def safe_startup(this_app: FastAPI, dsrc_inst: Source, config: Config):
    this_app.state.config = config
    dsrc_inst.init_gateway(config)


# We use the functions below, so we can also manually call them in tests

async def app_startup(dsrc_inst: Source):
    # Only startup events that do not work in all environments or require other processes to run belong here
    # Safe startup events with variables that depend on the environment, but should always be run, can be included in
    # the 'safe_startup()' above
    # Safe startup events that do not depend on the environment, can be included in the 'create_app()' above
    config = load_config()
    if config.APISERVER_ENV not in allowed_envs:
        raise RuntimeError("Runtime environment (env.toml) does not correspond to compiled environment (define.toml)! "
                           "Ensure defined variables are appropriate for the runtime environment before changing the "
                           "environment!")
    safe_startup(app, dsrc_inst, config)
    # Db connections, etc.
    await dsrc_inst.startup()


async def app_shutdown(dsrc_inst: Source):
    await dsrc_inst.shutdown()


# Hooks defined by FastAPI to run on startup and shutdown

@app.on_event("startup")
async def startup():
    dsrc: Source = app.state.dsrc
    logger.info("Running startup...")
    await app_startup(dsrc)


@app.on_event("shutdown")
async def shutdown():
    dsrc: Source = app.state.dsrc
    logger.info("Running shutdown...")
    await app_shutdown(dsrc)


@app.exception_handler(RequestValidationError)
def validation_exception_handler(request, exc: RequestValidationError):
    # Also show debug if there is an error in the request
    exc_str = str(exc)
    logger.debug(str(exc))
    return error_response_return(err_status_code=400, err_type="bad_request_validation", err_desc=exc_str)
