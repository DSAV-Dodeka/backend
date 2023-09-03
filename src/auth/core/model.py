from pydantic import BaseModel


class AuthRequest(BaseModel):
    response_type: str
    client_id: str
    redirect_uri: str
    state: str
    code_challenge: str
    code_challenge_method: str
    nonce: str


class PasswordRequest(BaseModel):
    email: str
    client_request: str


class SavedState(BaseModel):
    user_id: str
    user_email: str
    scope: str
    state: str


class SavedRegisterState(BaseModel):
    user_id: str


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
