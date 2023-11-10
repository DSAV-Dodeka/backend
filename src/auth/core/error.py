from typing import Optional, Literal, Union
from yarl import URL

from store.error import DataError

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


class RefreshOperationError(ValueError):
    """Invalid refresh token."""

    pass


class InvalidRefresh(Exception):
    """Invalid refresh token."""

    pass


ErrorDomain = Literal["data", "app"]


class UnexpectedError(Exception):
    domain: ErrorDomain
    key: str
    desc: str
    """An error that generally should not occur if the database and application are setup correctly."""


class UnexpectedDataError(Exception):
    def __init__(self, key: str, desc: str, e: DataError):
        self.domain = "data"
        self.key = key
        self.desc = desc
        self.int_err = e
