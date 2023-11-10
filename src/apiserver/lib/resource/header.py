from dataclasses import dataclass
from apiserver.lib.hazmat.tokens import BadVerification, get_kid, verify_access_token
from apiserver.lib.model.entities import AccessToken
from apiserver.lib.resource.error import ResourceError


@dataclass
class AccessSettings:
    grace_period: int
    issuer: str
    aud_client_ids: list[str]


def extract_token_and_kid(authorization: str) -> tuple[str, str]:
    if authorization is None:
        raise ResourceError(
            err_type="invalid_request", err_desc="No authorization provided."
        )
    if not authorization.startswith("Bearer "):
        raise ResourceError(
            err_type="invalid_request",
            err_desc="Authorization must follow 'Bearer' scheme",
        )
    token = authorization.removeprefix("Bearer ")

    try:
        kid = get_kid(token)
    except BadVerification as e:
        raise ResourceError(
            err_type="invalid_token",
            err_desc="Token verification failed!",
            debug_key=e.err_key,
        )

    return token, kid


def resource_verify_token(
    token: str, public_key: str, settings: AccessSettings
) -> AccessToken:
    try:
        return verify_access_token(
            token,
            public_key,
            settings.grace_period,
            settings.issuer,
            settings.aud_client_ids,
        )
    except BadVerification as e:
        raise ResourceError(
            err_type="invalid_token",
            err_desc="Token verification failed!",
            debug_key=e.err_key,
        )
