from typing import Literal, Union


class OperationError(Exception):
    pass


class RefreshOperationError(OperationError):
    """Invalid refresh token."""

    pass


AuthErrorTypes = Union[Literal["invalid_request"], Literal["invalid_token"]]
ErrorTypes = Union[AuthErrorTypes]


class InfoOperationError(OperationError):
    err_type: ErrorTypes
    err_desc: str
    debug_key: str

    def __init__(self, err_type: ErrorTypes, err_desc: str, debug_key: str = ""):
        self.err_type = err_type
        self.err_desc = err_desc
        self.debug_key = debug_key


class BadAuth(InfoOperationError):
    err_type: AuthErrorTypes

    def __init__(self, err_type: AuthErrorTypes, err_desc: str, debug_key: str = ""):
        super().__init__(err_type, err_desc, debug_key)
