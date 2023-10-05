from pydantic import field_validator, ValidationError

from auth.core.error import AuthError, RedirectError
from auth.core.model import AuthRequest
from auth.define import Define

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


def auth_request_validate(
    define: Define,
    response_type: str,
    client_id: str,
    redirect_uri: str,
    state: str,
    code_challenge: str,
    code_challenge_method: str,
    nonce: str,
) -> AuthRequest:
    if client_id != define.frontend_client_id:
        raise AuthError("invalid_request", "Unrecognized client ID!", "bad_client_id")

    if redirect_uri not in define.valid_redirects:
        raise AuthError(
            "invalid_request", "Unrecognized redirect for client!", "bad_redirect"
        )

    if response_type != "code":
        raise RedirectError(
            "unsupported_response_type",
            "Only 'code' response_type is supported!",
            redirect_uri,
        )

    try:
        auth_request = AuthRequestValidator(
            response_type=response_type,
            client_id=client_id,
            redirect_uri=redirect_uri,
            state=state,
            code_challenge=code_challenge,
            code_challenge_method=code_challenge_method,
            nonce=nonce,
        )
    except ValidationError as e:
        raise RedirectError(
            "invalid_request",
            error_desc=str(e.errors()),
            redirect_uri_base=redirect_uri,
        )

    return auth_request
