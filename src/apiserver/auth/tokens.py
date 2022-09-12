import secrets
import json
from secrets import token_urlsafe
import logging

from cryptography.fernet import InvalidToken
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from pydantic import ValidationError
import jwt
from jwt import PyJWTError, DecodeError, InvalidSignatureError, ExpiredSignatureError, InvalidTokenError

from apiserver.define.config import Config
from apiserver.env import LOGGER_NAME, id_exp, access_exp, refresh_exp, \
    grace_period
from apiserver.utilities import enc_b64url, dec_b64url
from apiserver.define.entities import SavedRefreshToken, RefreshToken, AccessToken, IdToken

__all__ = ['verify_access_token', 'InvalidRefresh', 'BadVerification', 'create_tokens', 'aes_from_symmetric',
           'finish_tokens', 'encode_token_dict', 'decrypt_old_refresh', 'verify_refresh', 'build_refresh_save']

logger = logging.getLogger(LOGGER_NAME)


def enc_dict(dct: dict) -> bytes:
    """ Convert dict to UTF-8-encoded bytes in JSON format. """
    return json.dumps(dct).encode('utf-8')


def dec_dict(encoded: bytes) -> dict:
    """ Convert UTF-8 bytes containing JSON to a dict. """
    return json.loads(encoded.decode('utf-8'))


class InvalidRefresh(Exception):
    """ Invalid refresh token. """
    pass


def encrypt_refresh(aesgcm: AESGCM, refresh: RefreshToken) -> str:
    refresh_data = enc_dict(refresh.dict())
    refresh_nonce = secrets.token_bytes(12)
    encrypted = aesgcm.encrypt(refresh_nonce, refresh_data, None)
    refresh_bytes = refresh_nonce + encrypted
    return enc_b64url(refresh_bytes)


def decrypt_refresh(aesgcm: AESGCM, refresh_token) -> RefreshToken:
    refresh_bytes = dec_b64url(refresh_token)
    refresh_nonce = refresh_bytes[:12]
    refresh_data = refresh_bytes[12:]
    decrypted = aesgcm.decrypt(refresh_nonce, refresh_data, None)
    refresh_dict = dec_dict(decrypted)
    return RefreshToken.parse_obj(refresh_dict)


def aes_from_symmetric(symmetric_key) -> AESGCM:
    # We store it unpadded (to match convention of not storing padding throughout the DB)
    symmetric_key_bytes = dec_b64url(symmetric_key)
    # We initialize an AES-GCM key class that will be used for encryption/decryption
    return AESGCM(symmetric_key_bytes)


def decrypt_old_refresh(aesgcm: AESGCM, old_refresh_token: str):
    # expects base64url-encoded binary
    try:
        # If it has been tampered with, this will also give an error
        old_refresh = decrypt_refresh(aesgcm, old_refresh_token)
    except InvalidToken:
        # Fernet error or signature error, could also be key format
        raise InvalidRefresh("InvalidToken")
    except ValidationError:
        # From parsing the dict
        raise InvalidRefresh("Bad validation")
    except ValueError:
        # For example from the JSON decoding
        raise InvalidRefresh("Other parsing")

    return old_refresh


def verify_refresh(saved_refresh: SavedRefreshToken, old_refresh: RefreshToken, utc_now: int) -> None:
    if saved_refresh.nonce != old_refresh.nonce or saved_refresh.family_id != old_refresh.family_id:
        raise InvalidRefresh("Bad comparison")
    elif saved_refresh.iat > utc_now or saved_refresh.iat < 1640690242:
        # sanity check
        raise InvalidRefresh
    elif utc_now > saved_refresh.exp + grace_period:
        # refresh no longer valid
        raise InvalidRefresh


def build_refresh_save(saved_refresh: SavedRefreshToken, utc_now: int):
    # Rebuild access and ID tokens from value in refresh token
    # We need the core static info to rebuild with new iat, etc.
    saved_access, saved_id_token = decode_refresh(saved_refresh)
    user_usph = saved_id_token.sub

    # Scope to be returned in response
    access_scope = saved_access.scope

    # Nonce is used to make it impossible to 'guess' new refresh tokens
    # (So it becomes a combination of family_id + id nr + nonce)
    # Although signing and encrypting should also protect it from that
    new_nonce = token_urlsafe(16).rstrip("=")
    # We don't store the access tokens and refresh tokens in the final token
    # To construct new tokens, we need that information so we save it in the DB
    new_refresh_save = SavedRefreshToken(family_id=saved_refresh.family_id,
                                         access_value=saved_refresh.access_value,
                                         id_token_value=saved_refresh.id_token_value, exp=saved_refresh.exp,
                                         iat=utc_now, nonce=new_nonce)

    return saved_access, saved_id_token, user_usph, access_scope, new_nonce, new_refresh_save


def build_refresh_token(new_refresh_id: int, saved_refresh: SavedRefreshToken, new_nonce: str, aesgcm: AESGCM):
    # The actual refresh token is an encrypted JSON dictionary containing the id, family_id and nonce
    refresh = RefreshToken(id=new_refresh_id, family_id=saved_refresh.family_id, nonce=new_nonce)
    refresh_token = encrypt_refresh(aesgcm, refresh)
    return refresh_token


def create_tokens(user_usph: str, scope: str, auth_time: int, id_nonce: str, utc_now: int, config: Config):
    # Build new tokens
    access_token_data, id_token_data = id_access_tokens(sub=user_usph,
                                                        iss=config.issuer,
                                                        aud_access=[config.frontend_client_id, config.backend_client_id],
                                                        aud_id=[config.frontend_client_id],
                                                        scope=scope,
                                                        auth_time=auth_time,
                                                        id_nonce=id_nonce)

    # Scope to be returned in response
    access_scope = access_token_data.scope

    # Encoded tokens to store for refresh token
    access_val_encoded = encode_token_dict(access_token_data.dict())
    id_token_val_encoded = encode_token_dict(id_token_data.dict())
    # Each authentication creates a refresh token of a particular family, which has a static lifetime
    family_id = secrets.token_urlsafe(16)
    refresh_save = SavedRefreshToken(family_id=family_id, access_value=access_val_encoded,
                                     id_token_value=id_token_val_encoded, exp=utc_now + refresh_exp, iat=utc_now,
                                     nonce="")
    return access_token_data, id_token_data, access_scope, refresh_save


def finish_tokens(refresh_id: int, refresh_save: SavedRefreshToken, aesgcm: AESGCM, access_token_data: AccessToken,
                  id_token_data: IdToken, utc_now: int, signing_key: str, *, nonce: str):
    refresh = RefreshToken(id=refresh_id, family_id=refresh_save.family_id, nonce=nonce)
    refresh_token = encrypt_refresh(aesgcm, refresh)

    access_token = finish_encode_token(access_token_data.dict(), utc_now, access_exp, signing_key)
    id_token = finish_encode_token(id_token_data.dict(), utc_now, id_exp, signing_key)

    return refresh_token, access_token, id_token


def id_access_tokens(sub, iss, aud_access, aud_id, scope, auth_time, id_nonce):
    """ Create ID and access token objects. """
    access_core = AccessToken(sub=sub,
                              iss=iss,
                              aud=aud_access,
                              scope=scope)
    id_core = IdToken(sub=sub,
                      iss=iss,
                      aud=aud_id,
                      auth_time=auth_time,
                      nonce=id_nonce)

    return access_core, id_core


def encode_token_dict(token: dict):
    return enc_b64url(enc_dict(token))


def finish_payload(token_val: dict, utc_now: int, exp: int):
    """ Add time-based information to static token dict. """
    payload_add = {
        "iat": utc_now,
        "exp": utc_now + exp,
    }
    payload = dict(token_val, **payload_add)
    return payload


def finish_encode_token(token_val: dict, utc_now: int, exp: int, key: str):
    finished_payload = finish_payload(token_val, utc_now, exp)
    return jwt.encode(finished_payload, key, algorithm="EdDSA")


def decode_refresh(rt: SavedRefreshToken):
    saved_access_dict = dec_dict(dec_b64url(rt.access_value))
    saved_access = AccessToken.parse_obj(saved_access_dict)
    saved_id_token_dict = dec_dict(dec_b64url(rt.id_token_value))
    saved_id_token = IdToken.parse_obj(saved_id_token_dict)

    return saved_access, saved_id_token


class BadVerification(Exception):
    """ Error during token verification. """

    def __init__(self, err_key: str):
        self.err_key = err_key


def verify_access_token(public_key: str, access_token: str, config: Config):
    try:
        decoded_payload = jwt.decode(access_token, public_key, algorithms=["EdDSA"], leeway=grace_period,
                                     require=["exp", "aud"], issuer=config.issuer, audience=[config.backend_client_id])
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
