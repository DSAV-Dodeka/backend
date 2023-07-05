import hashlib
import logging
from typing import Optional

from fastapi import APIRouter
from pydantic import field_validator, BaseModel, ValidationError

import apiserver.lib.utilities as util
from apiserver.lib.model.entities import AuthRequest
from apiserver.app.define import LOGGER_NAME, frontend_client_id, valid_redirects
from apiserver.app.error import ErrorResponse

router = APIRouter()

port_front = 3000

logger = logging.getLogger(LOGGER_NAME)


class TokenRequest(BaseModel):
    client_id: str
    grant_type: str
    code: Optional[str] = None
    redirect_uri: Optional[str] = None
    code_verifier: Optional[str] = None
    refresh_token: Optional[str] = None


class TokenResponse(BaseModel):
    id_token: str
    access_token: str
    refresh_token: str
    token_type: str
    expires_in: int
    scope: str


MAX_STR_LEN = 100
CODE_CHALLENGE_MAX = 128
CODE_CHALLENGE_MIN = 43


class AuthRequestValidator(AuthRequest):
    @field_validator("response_type")
    def check_type(cls, v: str) -> str:
        assert v == "code", "'response_type' must be 'code'"
        return v

    @field_validator("client_id")
    def check_client(cls, v: str) -> str:
        assert v == frontend_client_id, "Unrecognized client ID!"
        return v

    @field_validator("redirect_uri")
    def check_redirect(cls, v: str) -> str:
        assert v in valid_redirects, "Unrecognized redirect!"
        return v

    @field_validator("state")
    def check_state(cls, v: str) -> str:
        assert len(v) < MAX_STR_LEN, "State must not be too long!"
        return v

    # possibly replace for performance
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
    response_type,
    client_id,
    redirect_uri,
    state,
    code_challenge,
    code_challenge_method,
    nonce,
) -> AuthRequest:
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
        logger.debug(str(e.errors()))
        raise ErrorResponse(
            status_code=400, err_type="invalid_authorize", err_desc=str(e.errors())
        )

    return auth_request


def authorization_validate(token_request: TokenRequest):
    # This grant type requires other body parameters than the refresh token grant type
    try:
        assert token_request.redirect_uri
        assert token_request.code_verifier
        assert token_request.code
    except AssertionError:
        reason = "redirect_uri, code and code_verifier must be defined"
        logger.debug(reason)
        raise ErrorResponse(
            400,
            err_type="invalid_request",
            err_desc=reason,
            debug_key="incomplete_code",
        )


def compare_auth_token_validate(token_request: TokenRequest, auth_request: AuthRequest):
    if token_request.client_id != auth_request.client_id:
        logger.debug(
            f"Request redirect {token_request.client_id} does not match"
            f" {auth_request.client_id}"
        )
        raise ErrorResponse(
            400, err_type="invalid_request", err_desc="Incorrect client_id"
        )
    if token_request.redirect_uri != auth_request.redirect_uri:
        logger.debug(
            f"Request redirect {token_request.redirect_uri} does not match"
            f" {auth_request.redirect_uri}"
        )
        raise ErrorResponse(
            400, err_type="invalid_request", err_desc="Incorrect redirect_uri"
        )

    try:
        # We only support S256, so don't have to check the code_challenge_method
        computed_challenge_hash = hashlib.sha256(
            token_request.code_verifier.encode("ascii")
        ).digest()
        # Remove "=" as we do not store those
        challenge = util.enc_b64url(computed_challenge_hash)
    except UnicodeError:
        reason = "Incorrect code_verifier format"
        logger.debug(f"{reason}: {token_request.code_verifier}")
        raise ErrorResponse(400, err_type="invalid_request", err_desc=reason)
    if challenge != auth_request.code_challenge:
        logger.debug(
            f"Computed code challenge {challenge} does not match saved"
            f" {auth_request.code_challenge}"
        )
        raise ErrorResponse(
            400, err_type="invalid_grant", err_desc="Incorrect code_challenge"
        )


def refresh_validate(token_request: TokenRequest):
    try:
        assert token_request.refresh_token is not None
    except AssertionError as e:
        error_desc = "refresh_token must be defined"
        logger.debug(f"{str(e)}: {error_desc}")
        raise ErrorResponse(
            400, err_type="invalid_grant", err_desc="refresh_token must be defined"
        )
