from typing import Optional

from pydantic import BaseModel

HTTP_303_SEE_OTHER = 303


class Redirect(BaseModel):
    code: int
    url: str


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


class PasswordResponse(BaseModel):
    server_message: str
    auth_id: str
