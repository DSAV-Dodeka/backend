from enum import StrEnum
from typing import Optional

from fastapi import Request
from fastapi.responses import JSONResponse


class ErrorKeys(StrEnum):
    REGISTER = "invalid_register"
    RANKING_UPDATE = "invalid_ranking_update"
    DATA = "invalid_data_load"
    GET_CLASS = "invalid_get_class"
    CHECK = "invalid_code_check"
    UPDATE = "invalid_update"


class AppError(Exception):
    err_type: ErrorKeys
    err_desc: str
    debug_key: Optional[str]
    inner: Optional[Exception]

    def __init__(
        self,
        err_type: ErrorKeys,
        err_desc: str,
        debug_key: Optional[str] = None,
        inner: Optional[Exception] = None,
    ):
        super().__init__(err_desc)
        self.err_type = err_type
        self.err_desc = err_desc
        self.debug_key = debug_key
        self.inner = inner

    def to_message(self) -> str:
        debug_key = ":" + self.debug_key if self.debug_key is not None else ""
        return f"{self.err_type}{debug_key}: {self.err_desc}"


class ErrorResponse(Exception):
    """Exception response type that conforms to standard OAuth 2.0 error response in JSON form."""

    def __init__(
        self,
        status_code: int,
        err_type: str,
        err_desc: str,
        debug_key: Optional[str] = None,
    ):
        self.status_code = status_code
        self.err_type = err_type
        self.err_desc = err_desc
        self.debug_key = debug_key


def error_response_return(
    err_status_code: int,
    err_type: str,
    err_desc: str,
    err_debug_key: Optional[str] = None,
) -> JSONResponse:
    content = {"error": err_type, "error_description": err_desc}
    if err_debug_key is not None:
        content["debug_key"] = err_debug_key

    return JSONResponse(status_code=err_status_code, content=content)


def error_response_handler(_request: Request, e: ErrorResponse) -> JSONResponse:
    return error_response_return(e.status_code, e.err_type, e.err_desc, e.debug_key)


class AppEnvironmentError(Exception):
    pass
