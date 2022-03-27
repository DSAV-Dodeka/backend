from pydantic import BaseModel, validator


class User(BaseModel):
    id: int = None
    usp_hex: str
    password_file: str


class Key(BaseModel):
    id: int
    algorithm: str
    public: str
    private: str
    public_format: str
    public_encoding: str
    private_format: str
    private_encoding: str


class OpaqueKey(Key):
    @validator('algorithm')
    def validate_alg(cls, v):
        assert v == "curve25519ristretto"
        return v

    @validator('public_format')
    def validate_pub_fmt(cls, v):
        assert v == "none"
        return v

    @validator('public_encoding')
    def validate_pub_enc(cls, v):
        assert v == "base64url"
        return v

    @validator('private_format')
    def validate_priv_fmt(cls, v):
        assert v == "none"
        return v

    @validator('private_encoding')
    def validate_priv_enc(cls, v):
        assert v == "base64url"
        return v


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
    family_id: str
    access_value: str
    id_token_value: str
    iat: int
    exp: int
    nonce: str


class RefreshToken(BaseModel):
    id: int  # make required again
    family_id: str
    nonce: str


class AccessToken(BaseModel):
    sub: str
    iss: str
    aud: list[str]
    scope: str


class IdToken(BaseModel):
    sub: str
    iss: str
    aud: list[str]
    auth_time: int
    nonce: str
