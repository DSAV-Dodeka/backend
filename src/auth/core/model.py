from pydantic import BaseModel, field_validator
from pydantic_core.core_schema import FieldValidationInfo


class AuthRequest(BaseModel):
    response_type: str
    client_id: str
    redirect_uri: str
    state: str
    code_challenge: str
    code_challenge_method: str
    nonce: str


MAX_STR_LEN = 100
CODE_CHALLENGE_MAX = 128
CODE_CHALLENGE_MIN = 43


class AuthRequestValidator(AuthRequest):
    @field_validator("state")
    def check_state(cls, v: str) -> str:
        assert len(v) < MAX_STR_LEN, "State must not be too long!"
        return v

    @field_validator("code_challenge")
    def check_challenge(cls, v: str) -> str:
        assert (
            CODE_CHALLENGE_MAX >= len(v) >= CODE_CHALLENGE_MIN
        ), "Length must be 128 >= len >= 43!"
        for c in v:
            assert c.isalnum() or c in "-._~", "Invalid character in challenge!"
        return v

    @field_validator("code_challenge_method")
    def check_method(cls, v: str) -> str:
        assert v == "S256", "Only S256 is supported!"
        return v

    @field_validator("nonce")
    def check_nonce(cls, v: str) -> str:
        assert len(v) < MAX_STR_LEN, "Nonce must not be too long!"
        return v
