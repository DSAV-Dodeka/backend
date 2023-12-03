import inspect
import logging
import sys
from typing import Any
from fastapi import FastAPI, Request, Response
import loguru
from loguru import logger

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

from apiserver.env import Config
from auth.core.util import random_time_hash_hex


# copied from loguru docs
# https://loguru.readthedocs.io/en/0.7.2/overview.html#entirely-compatible-with-standard-logging
class InterceptHandler(logging.Handler):
    def emit(self, record: logging.LogRecord) -> None:
        # Get corresponding Loguru level if it exists.
        level: str | int
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        # Find caller from where originated the logged message.
        frame, depth = inspect.currentframe(), 0
        while frame and (depth == 0 or frame.f_code.co_filename == logging.__file__):
            frame = frame.f_back
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(
            level, record.getMessage()
        )


def intercept_logging(logger_names: list[str]) -> None:
    logging.basicConfig(handlers=[InterceptHandler()], level=0, force=True)
    for logger_name in logger_names:
        mod_logger = logging.getLogger(logger_name)
        mod_logger.handlers = [InterceptHandler()]
        mod_logger.propagate = False


def loguru_remove_default() -> None:
    logger.remove(0)


def enable_libraries() -> None:
    logger.enable("store")
    logger.enable("auth")
    logger.enable("datacontext")


def logger_format(record: "loguru.Record") -> str:
    extra = record["extra"]
    if "request_id" not in extra:
        extra["request_id"] = ""
    return (
        "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
        "- {extra[request_id]}<level>{message}</level>\n"
    )


def logger_stderr_sink() -> None:
    # Adapted from default loguru format

    logger.add(sys.stderr, colorize=True, format=logger_format, level="DEBUG")
    # logger = logger.patch(lambda record: record["extra"].update(utc=datetime.utcnow()))


# we need 'loguru.Message' due to the way Loguru's type hints work
def dict_sink(msg: "loguru.Message") -> None:
    # TODO implement
    pass


def logger_dict_sink(log_dict: dict[str, Any]) -> None:
    logger.add(dict_sink, format=logger_format, level="DEBUG")


# we need 'loguru.Message' due to the way Loguru's type hints work
def struct_file_sink(msg: "loguru.Message") -> None:
    # TODO implement
    pass


def logger_struct_file_sink(config: Config) -> None:
    # debug
    logger.add(struct_file_sink, format=logger_format, level="DEBUG")

    # trace
    logger.add(struct_file_sink, format=logger_format, level="TRACE")

    # warning
    logger.add(struct_file_sink, format=logger_format, level="WARNING")


class LoggerMiddleware(BaseHTTPMiddleware):
    """
    Logs every request and response. By default it logs at DEBUG level, but routes set in `trace_routes` are logged
    at TRACE level.
    """

    trace_routes: set[str]

    def __init__(self, app: FastAPI, trace_routes: set[str]) -> None:
        """
        Args:
            app: the FastAPI app that will use this middleware.
            trace_routes: set of routes that will not be logged at debug level but at trace level instead.
        """
        super().__init__(app)
        self.trace_routes = trace_routes

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        # For the static files we do not want debug logs for every request
        request_id = random_time_hash_hex(short=True) + ": "
        with logger.contextualize(request_id=request_id):
            req_path_parts = request.url.path.split("/")
            if len(req_path_parts) < 1:
                level = "DEBUG"
            else:
                level = "TRACE" if req_path_parts[1] in self.trace_routes else "DEBUG"

            logger.log(level, request.url.path)

            response = await call_next(request)
            logger.log(level, response.status_code)

        return response
