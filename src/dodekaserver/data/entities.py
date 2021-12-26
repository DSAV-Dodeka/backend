from pydantic import BaseModel


class User(BaseModel):
    id: int
    usp_hex: str
    password_file: str
