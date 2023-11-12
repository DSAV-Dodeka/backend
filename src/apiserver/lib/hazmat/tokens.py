from loguru import logger

import jwt
from jwt import (
    PyJWTError,
    DecodeError,
    InvalidSignatureError,
    ExpiredSignatureError,
    InvalidTokenError,
)

from apiserver.lib.model.entities import (
    AccessToken,
)

__all__ = [
    "verify_access_token",
    "BadVerification",
    "get_kid",
]


class BadVerification(Exception):
    """Error during token verification."""

    def __init__(self, err_key: str):
        self.err_key = err_key


def get_kid(access_token: str) -> str:
    try:
        unverified_header = jwt.get_unverified_header(access_token)
        return str(unverified_header["kid"])
    except KeyError:
        raise BadVerification("no_kid")
    except DecodeError:
        raise BadVerification("decode_error")
    except PyJWTError as e:
        logger.debug(e)
        raise BadVerification("other")


def verify_access_token(
    access_token: str,
    public_key: str,
    grace_period: int,
    issuer: str,
    audience: list[str],
) -> AccessToken:
    try:
        decoded_payload = jwt.decode(
            access_token,
            public_key,
            algorithms=["EdDSA"],
            leeway=grace_period,
            options={"require": ["exp", "aud"]},
            issuer=issuer,
            audience=audience,
        )
    except InvalidSignatureError:
        raise BadVerification("invalid_signature")
    except DecodeError:
        raise BadVerification("decode_error")
    except ExpiredSignatureError:
        raise BadVerification("expired_access_token")
    except InvalidTokenError:
        raise BadVerification("bad_token")
    except PyJWTError as e:
        logger.debug(e)
        raise BadVerification("other")

    return AccessToken.model_validate(decoded_payload)
