import logging
from contextlib import asynccontextmanager
from logging import Logger
from typing import TypedDict

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware import Middleware
from fastapi.middleware.cors import CORSMiddleware
from fastapi.routing import Mount
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.types import ASGIApp
from uvicorn.logging import DefaultFormatter

# Router modules, each router has its own API endpoints
import apiserver.lib.utilities as util
from apiserver.app.ops.startup import startup

# Import types separately to make it clear in what line the module is first loaded and
# its top-level run
from apiserver.data import Source
from apiserver.define import LOGGER_NAME, DEFINE
from apiserver.resources import res_path
from apiserver.app.error import (
    error_response_return,
    ErrorResponse,
    error_response_handler,
)
from apiserver.app.routers import (
    admin,
    basic,
    update_router,
    profile,
    users,
    onboard_router,
    auth_router,
)
from apiserver.env import load_config, Config


def init_logging(logger_name: str, log_level: int):
    logger_init = logging.getLogger(logger_name)
    logger_init.setLevel(log_level)
    str_handler = logging.StreamHandler()
    # handler = logging.FileHandler(filename=log_path)
    log_format = "%(levelprefix)s %(asctime)s | %(message)s "
    formatter = DefaultFormatter(log_format, datefmt="%Y-%m-%d %H:%M:%S")
    # handler.setFormatter(formatter)
    str_handler.setFormatter(formatter)
    # logger_init.addHandler(handler)
    logger_init.addHandler(str_handler)
    return logger_init


logger = init_logging(LOGGER_NAME, logging.DEBUG)


class LoggerMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp, mw_logger: Logger):
        super().__init__(app)
        self.mw_logger = mw_logger

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint):
        # self.mw_logger.debug(request.headers)
        return await call_next(request)


class State(TypedDict):
    dsrc: Source
    config: Config


@asynccontextmanager
async def lifespan(_app: FastAPI) -> State:
    logger.info("Running startup...")
    dsrc = Source()
    config = await app_startup(dsrc)
    yield {"dsrc": dsrc, "config": config}
    logger.info("Running shutdown...")
    await app_shutdown(dsrc)


async def validation_exception_handler(_request, exc: RequestValidationError):
    # Also show debug if there is an error in the request
    exc_str = str(exc)
    logger.debug(str(exc))
    return error_response_return(
        err_status_code=400, err_type="bad_request_validation", err_desc=exc_str
    )


def create_app(app_lifespan) -> FastAPI:
    # TODO change all origins
    origins = [
        "*",
    ]
    routes = [
        Mount(
            "/credentials",
            app=StaticFiles(
                directory=res_path.joinpath("static/credentials"), html=True
            ),
            name="credentials",
        )
    ]
    middleware = [
        Middleware(
            CORSMiddleware,
            allow_origins=origins,
            allow_methods=["*"],
            allow_headers=["Authorization"],
        ),
        Middleware(LoggerMiddleware, mw_logger=logger),
    ]

    exception_handlers = {RequestValidationError: validation_exception_handler}

    new_app = FastAPI(
        title="apiserver",
        routes=routes,
        middleware=middleware,
        lifespan=app_lifespan,
        exception_handlers=exception_handlers,
    )
    new_app.include_router(basic.router)
    new_app.include_router(auth_router)
    new_app.include_router(profile.router)
    new_app.include_router(onboard_router)
    new_app.include_router(update_router)
    new_app.include_router(admin.router)
    new_app.include_router(users.router)
    new_app.add_exception_handler(ErrorResponse, handler=error_response_handler)
    # TODO change logger behavior in tests

    logger.info("Starting...")

    return new_app


# Should always be manually run in tests
def safe_startup(dsrc_inst: Source, config: Config):
    dsrc_inst.store.init_objects(config)


# We use the functions below, so we can also manually call them in tests


async def app_startup(dsrc_inst: Source):
    # Only startup events that do not work in all environments or require other
    # processes to run belong here
    # Safe startup events with variables that depend on the environment, but should
    # always be run, can be included in the 'safe_startup()' above
    # Safe startup events that do not depend on the environment, can be included in
    # the 'create_app()' above

    config = load_config()

    if config.APISERVER_ENV not in DEFINE.allowed_envs:
        raise RuntimeError(
            "Runtime environment (env.toml) does not correspond to compiled environment"
            " (define.toml)! Ensure defined variables are appropriate for the runtime"
            " environment before changing the environment!"
        )
    if config.APISERVER_ENV == "localdev":
        cr_time = util.when_modified(res_path.joinpath("static/credentials"))
        src_time = util.when_modified(
            res_path.parent.parent.parent.joinpath("authpage/src")
        )
        if cr_time > src_time:
            logger.warning(
                "Most likely authpage has not been recently built for development,"
                " please run `npm run build` in /authpage directory."
            )

    safe_startup(dsrc_inst, config)
    # Db connections, etc.
    do_recreate = config.RECREATE == "yes"
    await startup(dsrc_inst, config, do_recreate)

    return config


async def app_shutdown(dsrc_inst: Source):
    await dsrc_inst.store.shutdown()
