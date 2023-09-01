from typing import Optional, Literal, Union
from yarl import URL


ErrorCode = Union[
    # All responses
    Literal["invalid_request"],
    Literal["invalid_scope"],
    # Only used if specific clients are not allowed to use specific grant types/challenge methods
    Literal["unauthorized_client"],
    # Token Response only
    Literal["invalid_client"],
    Literal["invalid_grant"],
    Literal["unsupported_grant_type"],
    # Auth Request only
    Literal["access_denied"],  # If resource owner or auth server denies the request
    Literal["unsupported_response_type"],  # If response_type != code
    Literal["server_error"],
    Literal["temporarily_unavailable"],
]
"""See section 4.1.2.1 (Error Response for authorization request) and Section 3.2.3.1 (Error Response for token
 request)"""


ResourceErrorCode = Union[
    Literal["invalid_request"],  # HTTP 400
    Literal["invalid_token"],  # HTTP 401
    Literal["insufficient_scope"],  # HTTP 403
]
"""https://www.rfc-editor.org/rfc/rfc6750.html#section-6.2 error codes for accessing resources. No error info should
be provided when no authentication information is provided."""


class AuthError(Exception):
    def __init__(
        self,
        err_type: ErrorCode,
        err_desc: str,
        debug_key: Optional[str] = None,
    ):
        self.err_type = err_type
        self.err_desc = err_desc
        self.debug_key = debug_key


class RedirectError(Exception):
    def __init__(
        self,
        error: ErrorCode,
        error_desc: str,
        redirect_uri_base: str,
        code: int = 303,
        error_uri: Optional[str] = None,
        debug_key: Optional[str] = None,
    ):
        uri_base = URL(redirect_uri_base)

        query = {"error": error, "error_description": error_desc}
        if error_uri is not None:
            query["error_uri"] = error_uri

        new_uri = uri_base.update_query(query)

        self.redirect_uri = str(new_uri)
        self.code = code
        self.debug_key = debug_key
