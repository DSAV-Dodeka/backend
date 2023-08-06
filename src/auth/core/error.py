from typing import Optional, Literal, Union


class AuthError(Exception):
    def __init__(
        self,
        err_type: str,
        err_desc: str,
        debug_key: Optional[str] = None,
    ):
        self.err_type = err_type
        self.err_desc = err_desc
        self.debug_key = debug_key


error_code = Union[
    Literal["invalid_request"],
    Literal["unauthorized_client"],
    Literal["access_denied"],
    Literal["unsupported_response_type"],
    Literal["invalid_scope"],
    Literal["server_error"],
    Literal["temporarily_unavailable"],
]


class RedirectError(Exception):
    def __init__(
        self,
        error: error_code,
        error_desc: str,
        error_uri: Optional[str] = None,
        debug_key: Optional[str] = None,
    ):
        self.error = error
        self.error_description = error_desc
        self.error_uri = error_uri
        self.debug_key = debug_key
