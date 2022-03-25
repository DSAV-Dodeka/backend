import logging
import uvicorn

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

# We rely upon database parameters being set at import time, which is fragile, but the only way to easily re-use it
# across modules
# In most cases this is where all environment variables and other configuration is loaded
from httpx import AsyncClient

from dodekaserver.env import res_path, LOGGER_NAME
from dodekaserver.data import dsrc
# Import types separately to make it clear in what line the module is first loaded and its top-level run
from dodekaserver.data import Source

from dodekaserver.define import ErrorResponse

# Router modules, each router has its own API endpoints
import dodekaserver.routers.basic as basic
import dodekaserver.routers.auth as auth
import dodekaserver.routers.profile as profile


def create_app() -> FastAPI:
    # TODO change all origins
    origins = [
        "*",
    ]

    new_app = FastAPI()
    new_app.mount("/credentials", StaticFiles(directory=res_path.joinpath("static/credentials")), name="credentials")
    new_app.include_router(basic.router)
    new_app.include_router(auth.router)
    new_app.include_router(profile.router)
    new_app.add_middleware(CORSMiddleware, allow_origins=origins, allow_methods=['*'],
                           allow_headers=['Authorization'])
    return new_app


# Running FastAPI relies on the fact the app is created at module top-level
# Seperating the logic in a function also allows it to be called elsewhere, like tests
app = create_app()


def init_logging(logger_name: str, log_level: int):
    logger = logging.getLogger(logger_name)
    logger.setLevel(log_level)
    handler = logging.StreamHandler()
    log_format = "%(levelprefix)s %(asctime)s | %(message)s"
    formatter = uvicorn.logging.DefaultFormatter(log_format, datefmt="%Y-%m-%d %H:%M:%S")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    return logger


# We use the functions below, so we can also manually call them in tests

async def app_startup(dsrc_inst: Source):
    logger = init_logging(LOGGER_NAME, logging.DEBUG)
    logger.info("Starting...")

    await dsrc_inst.connect()


async def app_shutdown(dsrc_inst: Source):
    await dsrc_inst.connect()


# Hooks defined by FastAPI to run on startup and shutdown

@app.on_event("startup")
async def startup():
    # It relies on dsrc from the module's top-level imports
    await app_startup(dsrc)


@app.on_event("shutdown")
async def shutdown():
    # It relies on dsrc from the module's top-level imports
    await app_shutdown(dsrc)


@app.exception_handler(ErrorResponse)
async def error_response_handler(request: Request, e: ErrorResponse):
    return JSONResponse(
        status_code=e.status_code,
        content={
            "error": e.err_type,
            "error_description": e.err_desc
        }
    )
