from pydantic import BaseModel


class OpaqueSetup(BaseModel):
    id: int
    value: str


class User(BaseModel):
    user_id: str
    email: str
    password_file: str
    scope: str
