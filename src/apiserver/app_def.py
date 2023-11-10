import logging
from logging import Logger
from typing import Any, Callable, Coroutine, Type, TypeAlias

from fastapi import FastAPI, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.middleware import Middleware
from fastapi.middleware.cors import CORSMiddleware
from fastapi.routing import Mount
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.types import ASGIApp
from uvicorn.logging import DefaultFormatter
from apiserver.app_lifespan import AppLifespan

# Import types separately to make it clear in what line the module is first loaded and
# its top-level run
from apiserver.define import LOGGER_NAME
from apiserver.resources import res_path
from apiserver.app.error import (
    error_response_return,
    ErrorResponse,
    error_response_handler,
)

# Router modules, each router has its own API endpoints
from apiserver.app.routers import (
    admin_router,
    basic,
    members_router,
    update,
    profile,
    onboard,
    auth_router,
    ranking,
)


def init_logging(logger_name: str, log_level: int) -> Logger:
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
    def __init__(self, app: ASGIApp, mw_logger: Logger) -> None:
        super().__init__(app)
        self.mw_logger = mw_logger

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        # self.mw_logger.debug(request.headers)
        return await call_next(request)


HandlerType: TypeAlias = Callable[[Request, Any], Coroutine[Any, Any, Response]]


def make_handler_dict(
    exc: int | Type[Exception], handler: HandlerType
) -> dict[int | Type[Exception], HandlerType]:
    return {exc: handler}


async def validation_exception_handler(
    _request: Any, exc: RequestValidationError | int
) -> Response:
    # Also show debug if there is an error in the request
    exc_str = str(exc)
    logger.debug(str(exc))
    return error_response_return(
        err_status_code=400, err_type="bad_request_validation", err_desc=exc_str
    )


def define_static_routes() -> list[Mount]:
    return [
        Mount(
            "/credentials",
            app=StaticFiles(
                directory=res_path.joinpath("static/credentials"), html=True
            ),
            name="credentials",
        )
    ]


def define_middleware() -> list[Middleware]:
    # TODO change all origins
    origins = [
        "*",
    ]

    return [
        Middleware(
            CORSMiddleware,
            allow_origins=origins,
            allow_methods=["*"],
            allow_headers=["Authorization"],
        ),
        Middleware(LoggerMiddleware, mw_logger=logger),
    ]


def add_routers(new_app: FastAPI) -> FastAPI:
    new_app.include_router(basic.router)
    new_app.include_router(auth_router)
    new_app.include_router(profile.router)
    new_app.include_router(onboard.router)
    new_app.include_router(update.router)
    new_app.include_router(ranking.old_router)

    admin_router.include_router(onboard.onboard_admin_router)
    admin_router.include_router(ranking.ranking_admin_router)
    members_router.include_router(ranking.ranking_members_router)

    new_app.include_router(admin_router)
    new_app.include_router(members_router)

    return new_app


def create_app(app_lifespan: AppLifespan) -> FastAPI:
    """App entrypoint."""

    routes = define_static_routes()
    middleware = define_middleware()

    exception_handlers = make_handler_dict(
        RequestValidationError, validation_exception_handler
    )

    new_app = FastAPI(
        title="apiserver",
        routes=routes,  # type: ignore
        middleware=middleware,
        lifespan=app_lifespan,
        exception_handlers=exception_handlers,
    )
    new_app = add_routers(new_app)

    new_app.add_exception_handler(ErrorResponse, handler=error_response_handler)

    # TODO change logger behavior in tests
    logger.info("Starting...")

    return new_app
