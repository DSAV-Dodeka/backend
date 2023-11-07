from enum import StrEnum


class DataError(Exception):
    key: str

    def __init__(self, message: str, key: str) -> None:
        self.message = message
        self.key = key


class NoDataError(DataError):
    pass


class DbErrors(StrEnum):
    INTEGRITY = "integrity_violation"
    INPUT = "invalid_input"


class DbError(Exception):
    """Exception that represents special internal errors."""

    def __init__(self, err_desc: str, err_internal: str, key: DbErrors) -> None:
        self.err_desc = err_desc
        self.err_internal = err_internal
        self.key = key
