import logging
from contextlib import asynccontextmanager
from typing import AsyncContextManager, AsyncIterator, Callable, TypedDict

from fastapi import FastAPI

from auth.data.context import Contexts
from auth.data.authentication import ctx_reg as auth_reg
from auth.data.authorize import ctx_reg as athrz_reg
from auth.data.keys import ctx_reg as key_reg
from auth.data.register import ctx_reg as register_reg
from auth.data.token import ctx_reg as token_reg


import apiserver.lib.utilities as util
from apiserver.app.ops.startup import startup
from apiserver.data import Source
from apiserver.data.context import Code, SourceContexts
from apiserver.data.context.register import ctx_reg as register_app_reg
from apiserver.data.context.update import ctx_reg as update_reg
from apiserver.data.context.ranking import ctx_reg as ranking_reg
from apiserver.data.context.authorize import ctx_reg as authrz_app_reg
from apiserver.define import LOGGER_NAME, DEFINE
from apiserver.env import load_config, Config
from apiserver.resources import res_path

logger = logging.getLogger(LOGGER_NAME)


class State(TypedDict):
    dsrc: Source
    cd: Code


# Should always be manually run in tests
def safe_startup(dsrc_inst: Source, config: Config) -> Source:
    dsrc_inst.config = config
    dsrc_inst.store.init_objects(config)

    return dsrc_inst


# We use the functions below, so we can also manually call them in tests


async def app_startup(dsrc_inst: Source) -> Source:
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

    dsrc_inst = safe_startup(dsrc_inst, config)
    # Db connections, etc.
    do_recreate = config.RECREATE == "yes"
    await startup(dsrc_inst, config, do_recreate)

    return dsrc_inst


async def app_shutdown(dsrc_inst: Source) -> None:
    await dsrc_inst.store.shutdown()


def register_and_define_code() -> Code:
    data_context = Contexts()
    data_context.include_registry(auth_reg)
    data_context.include_registry(athrz_reg)
    data_context.include_registry(key_reg)
    data_context.include_registry(register_reg)
    data_context.include_registry(token_reg)

    source_data_context = SourceContexts()
    source_data_context.include_registry(register_app_reg)
    source_data_context.include_registry(update_reg)
    source_data_context.include_registry(ranking_reg)
    source_data_context.include_registry(authrz_app_reg)

    return Code(
        auth_context=data_context,
        app_context=source_data_context,
    )


AppLifespan = Callable[[FastAPI], AsyncContextManager[State]]


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[State]:
    logger.info("Running startup...")
    dsrc = Source()
    dsrc_started = await app_startup(dsrc)
    yield {"dsrc": dsrc_started, "cd": register_and_define_code()}
    logger.info("Running shutdown...")
    await app_shutdown(dsrc_started)
