import secrets
from secrets import token_urlsafe
import logging

from cryptography.exceptions import InvalidTag, InvalidSignature, InvalidKey
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from pydantic import ValidationError
import jwt
from jwt import (
    PyJWTError,
    DecodeError,
    InvalidSignatureError,
    ExpiredSignatureError,
    InvalidTokenError,
)

import apiserver.lib.utilities as util
from apiserver.lib.errors import InvalidRefresh
from apiserver.lib.utilities.crypto import encrypt_dict, decrypt_dict
from apiserver.lib.model.entities import (
    SavedRefreshToken,
    RefreshToken,
    SavedAccessToken,
    IdToken,
    IdInfo,
    UserData,
    PEMKey,
    AccessToken,
)

__all__ = [
    "verify_access_token",
    "BadVerification",
    "create_tokens",
    "finish_tokens",
    "encode_token_dict",
    "decrypt_old_refresh",
    "verify_refresh",
    "build_refresh_save",
    "id_info_from_ud",
    "get_kid",
]


def encrypt_refresh(aesgcm: AESGCM, refresh: RefreshToken) -> str:
    return encrypt_dict(aesgcm, refresh.dict())


def decrypt_refresh(aesgcm: AESGCM, refresh_token) -> RefreshToken:
    refresh_dict = decrypt_dict(aesgcm, refresh_token)
    return RefreshToken.parse_obj(refresh_dict)


def decrypt_old_refresh(
    aesgcm: AESGCM, old_aesgcm: AESGCM, old_refresh_token: str, tried_old=False
):
    # expects base64url-encoded binary
    try:
        # If it has been tampered with, this will also give an error
        old_refresh = decrypt_refresh(aesgcm, old_refresh_token)
    except (InvalidTag, InvalidSignature, InvalidKey):
        # Retry with previous key
        if not tried_old:
            return decrypt_old_refresh(old_aesgcm, old_aesgcm, old_refresh_token, True)
        # Problem with the key cryptography
        raise InvalidRefresh("InvalidToken")
    except ValidationError:
        # From parsing the dict
        raise InvalidRefresh("Bad validation")
    except ValueError:
        # For example from the JSON decoding
        raise InvalidRefresh("Other parsing")

    return old_refresh


FIRST_SIGN_TIME = 1640690242


def verify_refresh(
    saved_refresh: SavedRefreshToken,
    old_refresh: RefreshToken,
    utc_now: int,
    grace_period: int,
) -> None:
    if (
        saved_refresh.nonce != old_refresh.nonce
        or saved_refresh.family_id != old_refresh.family_id
    ):
        raise InvalidRefresh("Bad comparison")
    elif saved_refresh.iat > utc_now or saved_refresh.iat < FIRST_SIGN_TIME:
        # sanity check
        raise InvalidRefresh
    elif utc_now > saved_refresh.exp + grace_period:
        # refresh no longer valid
        raise InvalidRefresh


def build_refresh_save(saved_refresh: SavedRefreshToken, utc_now: int):
    # Rebuild access and ID tokens from value in refresh token
    # We need the core static info to rebuild with new iat, etc.
    saved_access, saved_id_token = decode_refresh(saved_refresh)
    user_id = saved_id_token.sub

    # Scope to be returned in response
    access_scope = saved_access.scope

    # Nonce is used to make it impossible to 'guess' new refresh tokens
    # (So it becomes a combination of family_id + id nr + nonce)
    # Although signing and encrypting should also protect it from that
    new_nonce = token_urlsafe(16).rstrip("=")
    # We don't store the access tokens and refresh tokens in the final token
    # To construct new tokens, we need that information so we save it in the DB
    new_refresh_save = SavedRefreshToken(
        family_id=saved_refresh.family_id,
        access_value=saved_refresh.access_value,
        id_token_value=saved_refresh.id_token_value,
        exp=saved_refresh.exp,
        iat=utc_now,
        nonce=new_nonce,
        user_id=saved_refresh.user_id,
    )

    return (
        saved_access,
        saved_id_token,
        user_id,
        access_scope,
        new_nonce,
        new_refresh_save,
    )


def build_refresh_token(
    new_refresh_id: int,
    saved_refresh: SavedRefreshToken,
    new_nonce: str,
    aesgcm: AESGCM,
):
    # The actual refresh token is an encrypted JSON dictionary containing the id,
    # family_id and nonce
    refresh = RefreshToken(
        id=new_refresh_id, family_id=saved_refresh.family_id, nonce=new_nonce
    )
    refresh_token = encrypt_refresh(aesgcm, refresh)
    return refresh_token


def id_info_from_ud(ud: UserData):
    return IdInfo(
        email=ud.email,
        name=f"{ud.firstname} {ud.lastname}",
        given_name=ud.firstname,
        family_name=ud.lastname,
        nickname=ud.callname,
        preferred_username=ud.callname,
        birthdate=ud.birthdate.isoformat(),
    )


def create_tokens(
    user_id: str,
    scope: str,
    auth_time: int,
    id_nonce: str,
    utc_now: int,
    id_info: IdInfo,
    issuer: str,
    frontend_client_id: str,
    backend_client_id: str,
    refresh_exp: int,
):
    # Build new tokens
    access_token_data, id_token_data = id_access_tokens(
        sub=user_id,
        iss=issuer,
        aud_access=[frontend_client_id, backend_client_id],
        aud_id=[frontend_client_id],
        scope=scope,
        auth_time=auth_time,
        id_nonce=id_nonce,
        id_info=id_info,
    )

    # Scope to be returned in response
    access_scope = access_token_data.scope

    # Encoded tokens to store for refresh token
    access_val_encoded = encode_token_dict(access_token_data.dict())
    id_token_val_encoded = encode_token_dict(id_token_data.dict())
    # Each authentication creates a refresh token of a particular family, which
    # has a static lifetime
    family_id = secrets.token_urlsafe(16)
    refresh_save = SavedRefreshToken(
        family_id=family_id,
        access_value=access_val_encoded,
        id_token_value=id_token_val_encoded,
        exp=utc_now + refresh_exp,
        iat=utc_now,
        nonce="",
        user_id=user_id,
    )
    return access_token_data, id_token_data, access_scope, refresh_save


def finish_tokens(
    refresh_id: int,
    refresh_save: SavedRefreshToken,
    aesgcm: AESGCM,
    access_token_data: SavedAccessToken,
    id_token_data: IdToken,
    utc_now: int,
    signing_key: PEMKey,
    access_exp: int,
    id_exp: int,
    *,
    nonce: str,
):
    refresh = RefreshToken(id=refresh_id, family_id=refresh_save.family_id, nonce=nonce)
    refresh_token = encrypt_refresh(aesgcm, refresh)

    access_token = finish_encode_token(
        access_token_data.dict(), utc_now, access_exp, signing_key
    )
    id_token = finish_encode_token(id_token_data.dict(), utc_now, id_exp, signing_key)

    return refresh_token, access_token, id_token


def id_access_tokens(
    sub, iss, aud_access, aud_id, scope, auth_time, id_nonce, id_info: IdInfo
):
    """Create ID and access token objects."""
    access_core = SavedAccessToken(sub=sub, iss=iss, aud=aud_access, scope=scope)
    id_core = IdToken(
        **id_info.dict(),
        sub=sub,
        iss=iss,
        aud=aud_id,
        auth_time=auth_time,
        nonce=id_nonce,
    )

    return access_core, id_core


def encode_token_dict(token: dict):
    return util.enc_b64url(util.enc_dict(token))


def finish_payload(token_val: dict, utc_now: int, exp: int):
    """Add time-based information to static token dict."""
    payload_add = {
        "iat": utc_now,
        "exp": utc_now + exp,
    }
    payload = dict(token_val, **payload_add)
    return payload


def finish_encode_token(token_val: dict, utc_now: int, exp: int, key: PEMKey):
    finished_payload = finish_payload(token_val, utc_now, exp)
    return jwt.encode(
        finished_payload, key.private, algorithm="EdDSA", headers={"kid": key.kid}
    )


def decode_refresh(rt: SavedRefreshToken):
    saved_access_dict = util.dec_dict(util.dec_b64url(rt.access_value))
    saved_access = SavedAccessToken.parse_obj(saved_access_dict)
    saved_id_token_dict = util.dec_dict(util.dec_b64url(rt.id_token_value))
    saved_id_token = IdToken.parse_obj(saved_id_token_dict)

    return saved_access, saved_id_token


class BadVerification(Exception):
    """Error during token verification."""

    def __init__(self, err_key: str):
        self.err_key = err_key


def get_kid(access_token: str):
    try:
        unverified_header = jwt.get_unverified_header(access_token)
        return unverified_header["kid"]
    except KeyError:
        raise BadVerification("no_kid")
    except DecodeError:
        raise BadVerification("decode_error")
    except PyJWTError as e:
        logging.debug(e)
        raise BadVerification("other")


def verify_access_token(
    public_key: str,
    access_token: str,
    grace_period: int,
    issuer: str,
    backend_client_id: str,
):
    try:
        decoded_payload = jwt.decode(
            access_token,
            public_key,
            algorithms=["EdDSA"],
            leeway=grace_period,
            require=["exp", "aud"],
            issuer=issuer,
            audience=[backend_client_id],
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
        logging.debug(e)
        raise BadVerification("other")

    return AccessToken.parse_obj(decoded_payload)
