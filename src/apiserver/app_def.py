from loguru import logger
from typing import Any, Callable, Coroutine, Type, TypeAlias

from fastapi import FastAPI, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.middleware import Middleware
from fastapi.middleware.cors import CORSMiddleware
from fastapi.routing import Mount
from fastapi.staticfiles import StaticFiles
from apiserver.app.app_logging import LoggerMiddleware
from apiserver.app_lifespan import AppLifespan

# Import types separately to make it clear in what line the module is first loaded and
# its top-level run
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


ExceptionHandler: TypeAlias = Callable[[Request, Any], Coroutine[Any, Any, Response]]


def define_exception_handlers(
    exc: int | Type[Exception], handler: ExceptionHandler
) -> dict[int | Type[Exception], ExceptionHandler]:
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
    credential_mount = Mount(
        "/credentials",
        app=StaticFiles(directory=res_path.joinpath("static/credentials"), html=True),
        name="credentials",
    )

    return [credential_mount]


def define_middleware(routes_to_trace_log: set[str]) -> list[Middleware]:
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
        Middleware(LoggerMiddleware, trace_routes=routes_to_trace_log),
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

    static_routes = define_static_routes()
    # We need the top-level route names because we don't want the logs to be spammed with them
    static_paths = set(map(lambda r: r.path.removeprefix("/"), static_routes))
    middleware = define_middleware(routes_to_trace_log=static_paths)

    exception_handlers = define_exception_handlers(
        RequestValidationError, validation_exception_handler
    )

    new_app = FastAPI(
        title="apiserver",
        # Types don't work because BaseRoute is not covariant, which we can't control
        routes=static_routes,  # type: ignore
        middleware=middleware,
        lifespan=app_lifespan,
        exception_handlers=exception_handlers,
    )
    new_app = add_routers(new_app)
    new_app.add_exception_handler(ErrorResponse, handler=error_response_handler)

    return new_app
