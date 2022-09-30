from datetime import date
from typing import Optional, Literal

from pydantic import BaseModel, validator, conint


class User(BaseModel):
    id: int = None
    id_name: str
    user_id: str = None
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


class OpaqueSetup(BaseModel):
    id: int
    value: str


class TokenKey(Key):
    @validator('algorithm')
    def validate_alg(cls, v):
        assert v == "ed448"
        return v

    @validator('public_format')
    def validate_pub_fmt(cls, v):
        assert v == "X509PKCS#1"
        return v

    @validator('public_encoding')
    def validate_pub_enc(cls, v):
        assert v == "PEM"
        return v

    @validator('private_format')
    def validate_priv_fmt(cls, v):
        assert v == "PKCS#8"
        return v

    @validator('private_encoding')
    def validate_priv_enc(cls, v):
        assert v == "PEM"
        return v


class SymmetricKey(Key):
    public: str = None
    public_format: str = None
    public_encoding: str = None

    @validator('algorithm')
    def validate_alg(cls, v):
        assert v == "symmetric"
        return v

    @validator('private_format')
    def validate_priv_fmt(cls, v):
        assert v == "none"
        return v

    @validator('private_encoding')
    def validate_priv_enc(cls, v):
        assert v == "base64url"
        return v


class SavedRefreshToken(BaseModel):
    id: int = None
    user_id: str
    family_id: str
    access_value: str
    id_token_value: str
    iat: int
    exp: int
    nonce: str


class RefreshToken(BaseModel):
    id: conint(strict=True, ge=0)  # make required again
    family_id: str
    nonce: str


class AccessToken(BaseModel):
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


class JWKSRow(BaseModel):
    id: int
    encrypted_value: str


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


class A256GCMKey(BaseModel):
    kid: str
    symmetric: str  # base64url encoded symmetric 256-bit key
