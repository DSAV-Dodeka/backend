class ErrorResponse(Exception):
    def __init__(self, status_code: int, err_type: str, err_desc: str):
        self.status_code = status_code
        self.err_type = err_type
        self.err_desc = err_desc
