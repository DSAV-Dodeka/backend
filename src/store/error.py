class DataError(Exception):
    key: str

    def __init__(self, message, key):
        self.message = message
        self.key = key


class NoDataError(DataError):
    pass
