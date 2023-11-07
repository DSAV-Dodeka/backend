from pydantic import BaseModel


class OpaqueSetup(BaseModel):
    id: int
    value: str


class User(BaseModel):
    user_id: str
    email: str
    password_file: str
    scope: str


# class InfoContainer(BaseModel, Generic[UserDataT, IdInfoT]):
#     ud: UserDataT
#     id_info: IdInfoT


class SavedRefreshToken(BaseModel):
    # Set by the database
    id: int = -1
    user_id: str
    family_id: str
    access_value: str
    id_token_value: str
    iat: int
    exp: int
    nonce: str
