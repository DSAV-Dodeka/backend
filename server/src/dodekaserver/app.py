from fastapi import Depends, FastAPI

from dodekaserver.data import dsrc

import dodekaserver.basic as basic


def create_app() -> FastAPI:
    new_app = FastAPI()
    new_app.include_router(basic.router)
    return new_app


app = create_app()


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
