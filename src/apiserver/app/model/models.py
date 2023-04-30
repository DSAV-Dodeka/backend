from pydantic import BaseModel


class PasswordResponse(BaseModel):
    server_message: str
    auth_id: str
