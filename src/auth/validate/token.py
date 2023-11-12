import hashlib
from loguru import logger

from pydantic import ValidationError

from auth.core.error import AuthError
from auth.core.model import TokenRequest, CodeGrantRequest, AuthRequest
from auth.core.util import enc_b64url


def authorization_validate(req: TokenRequest) -> CodeGrantRequest:
    # This grant type requires other body parameters than the refresh token grant type
    try:
        return CodeGrantRequest.model_validate(req.model_dump())
    except ValidationError as e:
        raise AuthError(
            "invalid_request",
            err_desc=str(e.errors()),
            debug_key="invalid_auth_code_token_request",
        )


def compare_auth_token_validate(
    token_request: CodeGrantRequest, auth_request: AuthRequest
) -> None:
    if token_request.client_id != auth_request.client_id:
        logger.debug(
            f"Request redirect {token_request.client_id} does not match"
            f" {auth_request.client_id}"
        )
        raise AuthError(err_type="invalid_request", err_desc="Incorrect client_id")
    if token_request.redirect_uri != auth_request.redirect_uri:
        logger.debug(
            f"Request redirect {token_request.redirect_uri} does not match"
            f" {auth_request.redirect_uri}"
        )
        raise AuthError(err_type="invalid_request", err_desc="Incorrect redirect_uri")

    try:
        # We only support S256 (this is checked before), so don't have to check the code_challenge_method
        computed_challenge_hash = hashlib.sha256(
            token_request.code_verifier.encode("ascii")
        ).digest()
        # Remove "=" as we do not store those
        challenge = enc_b64url(computed_challenge_hash)
    except UnicodeError:
        reason = "Incorrect code_verifier format"
        logger.debug(f"{reason}: {token_request.code_verifier}")
        raise AuthError(err_type="invalid_request", err_desc=reason)
    if challenge != auth_request.code_challenge:
        logger.debug(
            f"Computed code challenge {challenge} does not match saved"
            f" {auth_request.code_challenge}"
        )
        raise AuthError(err_type="invalid_grant", err_desc="Incorrect code_challenge")


def refresh_validate(req: TokenRequest) -> str:
    if req.refresh_token is None:
        error_desc = "refresh_token must be defined"
        logger.debug(f"{error_desc}")
        raise AuthError(
            err_type="invalid_grant", err_desc="refresh_token must be defined"
        )

    return req.refresh_token
