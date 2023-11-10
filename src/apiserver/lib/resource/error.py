from typing import Literal, Optional, Union


ResourceErrorCode = Union[
    Literal["invalid_request"],  # HTTP 400
    Literal["invalid_token"],  # HTTP 401
    Literal["insufficient_scope"],  # HTTP 403
]
"""https://www.rfc-editor.org/rfc/rfc6750.html#section-6.2 error codes for accessing resources. No error info should
be provided when no authentication information is provided."""


class ResourceError(Exception):
    err_type: ResourceErrorCode
    err_desc: str
    debug_key: Optional[str]

    def __init__(
        self,
        err_type: ResourceErrorCode,
        err_desc: str,
        debug_key: Optional[str] = None,
    ):
        super().__init__(err_desc)
        self.err_type = err_type
        self.err_desc = err_desc
        self.debug_key = debug_key


def resource_error_code(err_type: ResourceErrorCode) -> int:
    match err_type:
        case "invalid_request":
            return 400
        case "invalid_token":
            return 401
        case "insufficient_scope":
            return 403
        case _:
            raise ValueError(f"Incorrect error type for resource error: {err_type}")
