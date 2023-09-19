import typing

from fastapi.responses import JSONResponse


class RawJSONResponse(JSONResponse):
    def __init__(
        self,
        content: bytes,
        status_code: int = 200,
        headers: typing.Optional[typing.Dict[str, str]] = None,
    ) -> None:
        super().__init__(content, status_code, headers)

    def render(self, content: bytes) -> bytes:
        return content
