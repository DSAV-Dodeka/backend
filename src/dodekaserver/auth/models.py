from typing import Optional
from pydantic import BaseModel, validator


__all__ = ['AuthRequest', 'PasswordRequest', 'PasswordResponse', 'SavedState', 'FinishRequest', 'FinishLogin',
           'FlowUser', 'TokenRequest', 'TokenResponse']


class AuthRequest(BaseModel):
    response_type: str
    client_id: str
    redirect_uri: str
    state: str
    code_challenge: str
    code_challenge_method: str
    nonce: str

    @validator('response_type')
    def check_type(cls, v):
        assert v == "code", "'response_type' must be 'code'"
        return v

    @validator('client_id')
    def check_client(cls, v):
        assert v == "dodekaweb_client", "Unrecognized client ID!"
        return v

    @validator('redirect_uri')
    def check_redirect(cls, v):
        assert v == "http://localhost:3000/auth/callback", "Unrecognized redirect!"
        return v

    @validator('state')
    def check_state(cls, v):
        assert len(v) < 100, "State must not be too long!"
        return v

    # possibly replace for performance
    @validator('code_challenge')
    def check_challenge(cls, v: str):
        assert 128 >= len(v) >= 43, "Length must be 128 >= len >= 43!"
        for c in v:
            assert c.isalnum() or c in "-._~", "Invalid character in challenge!"
        return v

    @validator('nonce')
    def check_nonce(cls, v: str):
        assert len(v) < 100, "Nonce must not be too long!"
        return v


class PasswordRequest(BaseModel):
    """
    :var username: Username string, any valid Unicode works
    :var client_request: serialized (base64url-encoded) opaque-ke RegistrationUpload using the same cipher suite as the
        backend server
    """
    username: str
    client_request: str


class PasswordResponse(BaseModel):
    server_message: str
    auth_id: str


class SavedState(BaseModel):
    user_usph: str
    state: str


class FinishRequest(BaseModel):
    auth_id: str
    username: str
    client_request: str


class FinishLogin(BaseModel):
    auth_id: str
    username: str
    client_request: str
    flow_id: str


class FlowUser(BaseModel):
    user_usph: str
    flow_id: str
    auth_time: int


class TokenRequest(BaseModel):
    client_id: str
    grant_type: str
    code: Optional[str]
    redirect_uri: Optional[str]
    code_verifier: Optional[str]
    refresh_token: Optional[str]


class TokenResponse(BaseModel):
    id_token: str
    access_token: str
    refresh_token: str
    token_type: str
    expires_in: int
    scope: str
