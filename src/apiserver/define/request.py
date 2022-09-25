from typing import Optional
from datetime import date

from fastapi import Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, validator

from apiserver.define import frontend_client_id, valid_redirects


class ErrorResponse(Exception):
    """ Exception response type that conforms to standard OAuth 2.0 error response in JSON form. """
    def __init__(self, status_code: int, err_type: str, err_desc: str, debug_key: str = None):
        self.status_code = status_code
        self.err_type = err_type
        self.err_desc = err_desc
        self.debug_key = debug_key


def error_response_return(err_status_code: int, err_type: str, err_desc: str, err_debug_key: str = None):
    content = {
        "error": err_type,
        "error_description": err_desc
    }
    if err_debug_key is not None:
        content["debug_key"] = err_debug_key

    return JSONResponse(
        status_code=err_status_code,
        content=content
    )


def error_response_handler(request: Request, e: ErrorResponse):
    return error_response_return(e.status_code, e.err_type, e.err_desc, e.debug_key)


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
        assert v == frontend_client_id, "Unrecognized client ID!"
        return v

    @validator('redirect_uri')
    def check_redirect(cls, v):
        assert v in valid_redirects, "Unrecognized redirect!"
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

    @validator('code_challenge_method')
    def check_method(cls, v: str):
        assert v == "S256", "Only S256 is supported!"
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
    email: str
    client_request: str


class RegisterRequest(BaseModel):
    email: str
    client_request: str
    register_id: str


class PasswordResponse(BaseModel):
    server_message: str
    auth_id: str


class SavedRegisterState(BaseModel):
    user_usph: str
    id: int


class SavedState(BaseModel):
    user_usph: str
    user_id: int
    scope: str
    state: str


class FinishRequest(BaseModel):
    auth_id: str
    email: str
    client_request: str
    register_id: str
    callname: str
    eduinstitution: str
    birthdate: date


class FinishLogin(BaseModel):
    auth_id: str
    email: str
    client_request: str
    flow_id: str


class FlowUser(BaseModel):
    user_usph: str
    user_id: int
    scope: str
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


class SignupRequest(BaseModel):
    firstname: str
    lastname: str
    email: str
    phone: str


class EmailConfirm(BaseModel):
    confirm_id: str


class SignupConfirm(BaseModel):
    email: str
    av40id: int
    joined: date


class UserDataRegisterResponse(BaseModel):
    firstname: str
    lastname: str
    email: str
    phone: str


class ChangePasswordRequest(BaseModel):
    email: str


class UpdatePasswordRequest(BaseModel):
    email: str
    flow_id: str
    client_request: str


class UpdatePasswordFinish(BaseModel):
    auth_id: str
    client_request: str
