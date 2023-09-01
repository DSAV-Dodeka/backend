import hashlib
import logging
from typing import Optional

from fastapi import APIRouter
from pydantic import BaseModel

import auth.core.util
from apiserver.define import LOGGER_NAME
from apiserver.lib.model.entities import AuthRequest
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
        challenge = auth.core.util.enc_b64url(computed_challenge_hash)
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
