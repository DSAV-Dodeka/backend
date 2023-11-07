from dataclasses import dataclass
from typing import Optional

from pydantic import BaseModel, Field

from auth.hazmat.structs import SymmetricKey, PEMPrivateKey


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


class TokenRequest(BaseModel):
    client_id: str
    grant_type: str
    code: Optional[str] = None
    redirect_uri: Optional[str] = None
    code_verifier: Optional[str] = None
    refresh_token: Optional[str] = None


class CodeGrantRequest(BaseModel):
    code: str = Field(min_length=1)
    redirect_uri: str = Field(min_length=1)
    code_verifier: str = Field(min_length=1)
    client_id: str


class Tokens(BaseModel):
    id: str
    acc: str
    refr: str
    exp: int
    scope: str
    user_id: str


class TokenResponse(BaseModel):
    id_token: str
    access_token: str
    refresh_token: str
    token_type: str
    expires_in: int
    scope: str


class KeyState(BaseModel):
    """These are not the actual keys, just their IDs."""

    current_symmetric: str
    old_symmetric: str
    current_signing: str


class RefreshToken(BaseModel):
    id: int
    family_id: str
    nonce: str


class IdTokenBase(BaseModel):
    sub: str
    iss: str
    aud: list[str]
    auth_time: int
    nonce: str


class AccessTokenBase(BaseModel):
    sub: str
    iss: str
    aud: list[str]
    scope: str


@dataclass
class AuthKeys:
    symmetric: SymmetricKey
    old_symmetric: SymmetricKey
    signing: PEMPrivateKey
