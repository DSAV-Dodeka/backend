from fastapi import Request
from fastapi.responses import JSONResponse


class ErrorResponse(Exception):
    """ Exception response type that conforms to standard OAuth 2.0 error response in JSON form. """
    def __init__(self, status_code: int, err_type: str, err_desc: str, debug_key: str = None):
        self.status_code = status_code
        self.err_type = err_type
        self.err_desc = err_desc
        self.debug_key = debug_key


async def error_response_handler(request: Request, e: ErrorResponse):
    content = {
        "error": e.err_type,
        "error_description": e.err_desc
    }
    if e.debug_key is not None:
        content["debug_key"] = e.debug_key

    return JSONResponse(
        status_code=e.status_code,
        content=content
    )
