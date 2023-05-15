from datetime import date
from typing import Optional, Literal

from pydantic import BaseModel, validator


class User(BaseModel):
    # Set by the database
    id: int = -1
    id_name: str
    # Computed in the database
    user_id: str = ""
    email: str
    password_file: str
    scope: str = "member"


class Key(BaseModel):
    id: int
    algorithm: str
    public: str
    private: str
    public_format: str
    public_encoding: str
    private_format: str
    private_encoding: str


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


class RefreshToken(BaseModel):
    id: int
    family_id: str
    nonce: str


class AccessToken(BaseModel):
    sub: str
    iss: str
    aud: list[str]
    scope: str
    iat: int
    exp: int


class SavedAccessToken(BaseModel):
    sub: str
    iss: str
    aud: list[str]
    scope: str


class IdInfo(BaseModel):
    email: str
    name: str
    given_name: str
    family_name: str
    nickname: str
    preferred_username: str
    birthdate: str


class IdToken(IdInfo):
    sub: str
    iss: str
    aud: list[str]
    auth_time: int
    nonce: str


class SignedUp(BaseModel):
    firstname: str
    lastname: str
    email: str
    phone: str
    confirmed: bool = False


class UserData(BaseModel):
    user_id: str
    active: bool
    firstname: str
    lastname: str
    callname: str = ""
    email: str
    phone: str
    av40id: int
    joined: date
    eduinstitution: str = ""
    birthdate: date = date.min
    registerid: str = ""
    registered: bool
    showage: bool

    # Coerces null in database to false
    @validator("showage", pre=True)
    def parse_field3_as_bar(cls, value):
        if value is None:
            return False
        else:
            return value


class ScopeData(BaseModel):
    scope: str


class BirthdayData(BaseModel):
    firstname: str
    lastname: str
    birthdate: date = date.min


class RawUserScopeData(BaseModel):
    firstname: str
    lastname: str
    user_id: str
    scope: str


class UserScopeData(BaseModel):
    name: str
    user_id: str
    scope: list[str]


class EasterEggData(BaseModel):
    easter_egg_id: str


class JWKSRow(BaseModel):
    id: int
    encrypted_value: str


class A256GCMKey(BaseModel):
    kid: str
    symmetric: str  # base64url encoded symmetric 256-bit key


class OpaqueSetup(BaseModel):
    id: int
    value: str


class JWK(BaseModel):
    kty: Literal["okp", "oct"]
    use: Literal["sig", "enc"]
    alg: Literal["EdDSA", "A256GCM"]
    kid: str
    crv: Optional[Literal["Ed448"]]
    k: Optional[str]  # symmetric key base64url bytes
    x: Optional[str]  # public asymmetric key base64url bytes
    d: Optional[str]  # private asymmetric key base64url bytes


class JWKSet(BaseModel):
    keys: list[JWK]


class PEMKey(BaseModel):
    kid: str
    public: str  # PEM encoded X509PKCS#1 as unicode
    private: str  # PEM encoded PKCS#8 as unicode


class AuthRequest(BaseModel):
    response_type: str
    client_id: str
    redirect_uri: str
    state: str
    code_challenge: str
    code_challenge_method: str
    nonce: str


class SavedRegisterState(BaseModel):
    user_id: str


class SavedState(BaseModel):
    user_id: str
    user_email: str
    scope: str
    state: str


class FlowUser(BaseModel):
    user_id: str
    scope: str
    flow_id: str
    auth_time: int


class UpdateEmailState(BaseModel):
    user_id: str
    old_email: str
    new_email: str


class Signup(BaseModel):
    firstname: str
    lastname: str
    email: str
    phone: str


class Classification(BaseModel):
    type: str
    start_date: date
    end_date: date
    hidden_date: date
    last_updated: date


class ClassPoints(BaseModel):
    user_id: str
    classification_id: str
    true_points: str
    display_points: str


class UserID(BaseModel):
    user_id: str


class UserNames(BaseModel):
    user_id: str
    firstname: str
    lastname: str


class ClassView(BaseModel):
    classification_id: int
    last_updated: date


class UserPoints(BaseModel):
    name: str
    points: int
