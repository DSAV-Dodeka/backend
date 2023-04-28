from typing import Optional
from datetime import date


from pydantic import BaseModel, validator

from apiserver.app.define import frontend_client_id, valid_redirects


MAX_STR_LEN = 100
CODE_CHALLENGE_MAX = 128
CODE_CHALLENGE_MIN = 43


class AuthRequest(BaseModel):
    response_type: str
    client_id: str
    redirect_uri: str
    state: str
    code_challenge: str
    code_challenge_method: str
    nonce: str

    @validator("response_type")
    def check_type(cls, v: str) -> str:
        assert v == "code", "'response_type' must be 'code'"
        return v

    @validator("client_id")
    def check_client(cls, v: str) -> str:
        assert v == frontend_client_id, "Unrecognized client ID!"
        return v

    @validator("redirect_uri")
    def check_redirect(cls, v: str) -> str:
        assert v in valid_redirects, "Unrecognized redirect!"
        return v

    @validator("state")
    def check_state(cls, v: str) -> str:
        assert len(v) < MAX_STR_LEN, "State must not be too long!"
        return v

    # possibly replace for performance
    @validator("code_challenge")
    def check_challenge(cls, v: str) -> str:
        assert (
            CODE_CHALLENGE_MAX >= len(v) >= CODE_CHALLENGE_MIN
        ), "Length must be 128 >= len >= 43!"
        for c in v:
            assert c.isalnum() or c in "-._~", "Invalid character in challenge!"
        return v

    @validator("code_challenge_method")
    def check_method(cls, v: str) -> str:
        assert v == "S256", "Only S256 is supported!"
        return v

    @validator("nonce")
    def check_nonce(cls, v: str) -> str:
        assert len(v) < MAX_STR_LEN, "Nonce must not be too long!"
        return v


class PasswordRequest(BaseModel):
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
    user_id: str


class SavedState(BaseModel):
    user_id: str
    user_email: str
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
    age_privacy: bool


class FinishLogin(BaseModel):
    auth_id: str
    email: str
    client_request: str
    flow_id: str


class FlowUser(BaseModel):
    user_id: str
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


class UpdateEmail(BaseModel):
    user_id: str
    new_email: str


class UpdateEmailState(BaseModel):
    user_id: str
    old_email: str
    new_email: str


class UpdateEmailCheck(BaseModel):
    flow_id: str
    code: str


class ChangedEmailResponse(BaseModel):
    old_email: str
    new_email: str


class DeleteAccount(BaseModel):
    user_id: str


class DeleteUrlResponse(BaseModel):
    delete_url: str


class DeleteAccountCheck(BaseModel):
    flow_id: str
    code: str


class LogoutRequest(BaseModel):
    refresh_token: str


class ScopeAddRequest(BaseModel):
    user_id: str
    scope: str


class ScopeRemoveRequest(BaseModel):
    user_id: str
    scope: str
