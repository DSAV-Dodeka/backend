from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

# We rely upon database parameters being set at import time, which is fragile, but the only way to easily re-use it
# across modules
from dodekaserver.data import dsrc

import dodekaserver.basic as basic
import dodekaserver.auth as auth


def create_app() -> FastAPI:
    # TODO change all origins
    origins = [
        "*",
    ]

    new_app = FastAPI()
    new_app.include_router(basic.router)
    new_app.add_middleware(CORSMiddleware, allow_origins=origins, allow_methods=['*'])
    return new_app


app = create_app()


# We use the functions below so we can also manually call them in tests

async def app_startup(dsrc_inst):
    await dsrc_inst.connect()


async def app_shutdown(dsrc_inst):
    await dsrc_inst.connect()


@app.on_event("startup")
async def startup():
    await app_startup(dsrc)


@app.on_event("shutdown")
async def shutdown():
    await app_shutdown(dsrc)
