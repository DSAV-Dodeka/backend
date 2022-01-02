import secrets
import json
from secrets import token_urlsafe

from datetime import datetime, timezone

from cryptography.fernet import Fernet, InvalidToken
from pydantic import ValidationError
import jwt
from jwt import PyJWTError

from dodekaserver.utilities import add_base64_padding, encb64url_str, decb64url_str
import dodekaserver.data as data
from dodekaserver.data.entities import SavedRefreshToken, RefreshToken, AccessToken, IdToken
from dodekaserver.data import Source, DataError

__all__ = ['create_refresh_access_pair', 'create_id_token', 'verify_access_token', 'InvalidRefresh']

id_exp = 10 * 60 * 60  # 10 hours
access_exp = 1 * 60 * 60  # 1 hour
refresh_exp = 30 * 24 * 60 * 60  # 1 month

grace_period = 3 * 60  # 3 minutes in which it is still accepted

issuer = "https://dsavdodeka.nl/auth"
backend_client_id = "dodekabackend_client"


def _encode_json_dict(dct: dict) -> bytes:
    return json.dumps(dct).encode('utf-8')


def _decode_json_dict(encoded: bytes) -> dict:
    return json.loads(encoded.decode('utf-8'))


async def create_id_token(user_usph: str, auth_time: int, nonce: str, dsrc: Source = None, private_key=None):
    # TODO implement ID token
    utc_now = int(datetime.now(timezone.utc).timestamp())
    if auth_time == -1:
        auth_time = utc_now
    elif auth_time > utc_now or auth_time < 1640690242:
        # Prevent weird timestamps
        # The literal timestamp is 28/12/21
        raise ValueError("Invalid timestamp!")

    payload = {
        "sub": user_usph,
        "iss": issuer,
        "aud": "dodekaweb_client",
        "iat": utc_now,
        "exp": utc_now + id_exp,
        "auth_time": auth_time,
        "nonce": nonce
    }
    if dsrc is not None:
        private_key = await data.key.get_token_private(dsrc)
    return jwt.encode(payload, private_key, algorithm="EdDSA")


class InvalidRefresh(Exception):
    pass


async def create_refresh_access_pair(dsrc: Source, user_usph: str = None, scope: str = None, id_nonce: str = None,
                                     auth_time: int = None, refresh_token: str = None):
    """
    :return: Tuple of access token, refresh token, token_type, access expiration in seconds, scope, respectively.
    """

    # ENSURE scope is validated by the server first, do not pass directly from client

    symmetric_key = await data.key.get_refresh_symmetric(dsrc)
    padded_symmetric_key = add_base64_padding(symmetric_key)
    fernet = Fernet(padded_symmetric_key)
    signing_key = await data.key.get_token_private(dsrc)

    utc_now = int(datetime.now(timezone.utc).timestamp())

    token_type = "Bearer"

    if refresh_token is not None:
        # expects base64url-encoded binary
        try:
            decrypted = fernet.decrypt(refresh_token.encode('utf-8'))
            refresh_dict = _decode_json_dict(decrypted)
            refresh = RefreshToken.parse_obj(refresh_dict)
        except InvalidToken:
            # Fernet error or signature error, could also be key format
            raise InvalidRefresh
        except ValidationError:
            # From parsing the dict
            raise InvalidRefresh
        except ValueError:
            # For example from the JSON decoding
            raise InvalidRefresh

        try:
            saved_refresh = await data.refreshtoken.get_refresh_by_id(dsrc, refresh.id)
        except DataError as e:
            if e.key != "refresh_empty":
                raise e
            await data.refreshtoken.delete_family(dsrc, refresh.family_id)
            raise InvalidRefresh

        if saved_refresh.nonce != refresh.nonce or saved_refresh.family_id != refresh.family_id:
            raise InvalidRefresh
        elif saved_refresh.iat > utc_now or saved_refresh.iat < 1640690242:
            # sanity check
            raise InvalidRefresh
        elif utc_now > saved_refresh.exp + grace_period:
            # refresh no longer valid
            raise InvalidRefresh

        saved_access_dict = _decode_json_dict(decb64url_str(saved_refresh.access_value))
        saved_access = AccessToken.parse_obj(saved_access_dict)
        access_scope = saved_access.scope
        saved_id_token_dict = _decode_json_dict(decb64url_str(saved_refresh.id_token_value))
        saved_id_token = IdToken.parse_obj(saved_id_token_dict)
        new_access_payload = finish_token(saved_access.dict(), utc_now)
        new_id_token_payload = finish_token(saved_id_token.dict(), utc_now)

        access_token = jwt.encode(new_access_payload, signing_key, algorithm="EdDSA")
        id_token = jwt.encode(new_id_token_payload, signing_key, algorithm="EdDSA")

        new_nonce = token_urlsafe(16)
        new_refresh_save = SavedRefreshToken(family_id=saved_refresh.family_id,
                                             access_value=saved_refresh.access_value,
                                             id_token_value=saved_refresh.id_token_value, exp=saved_refresh.exp,
                                             iat=utc_now, nonce=new_nonce)
        new_refresh_id = await data.refreshtoken.refresh_transaction(dsrc, saved_refresh.id, new_refresh_save)

        refresh = RefreshToken(id=new_refresh_id, family_id=saved_refresh.family_id, nonce=new_nonce)
        refresh_token = fernet.encrypt(_encode_json_dict(refresh.dict())).decode('utf-8')
    else:
        assert user_usph is not None
        assert scope is not None
        assert id_nonce is not None
        assert auth_time is not None

        access_val, id_token_val = id_access_tokens(sub=user_usph,
                                                    iss="https://dsavdodeka.nl/auth",
                                                    aud_access=["dodekaweb_client", "dodekabackend_client"],
                                                    aud_id=["dodekaweb_client"],
                                                    scope=scope,
                                                    auth_time=auth_time,
                                                    id_nonce=id_nonce)

        access_scope = access_val.scope

        access_val_encoded = encb64url_str(_encode_json_dict(access_val.dict()))
        id_token_val_encoded = encb64url_str(_encode_json_dict(id_token_val.dict()))
        family_id = secrets.token_urlsafe(16)
        refresh_save = SavedRefreshToken(family_id=family_id, access_value=access_val_encoded,
                                         id_token_value=id_token_val_encoded, exp=utc_now + refresh_exp, iat=utc_now,
                                         nonce="")
        refresh_id = await data.refreshtoken.refresh_save(dsrc, refresh_save)
        refresh = RefreshToken(id=refresh_id, family_id=refresh_save.family_id, nonce="")

        # the bytes are base64url-encoded
        refresh_token = fernet.encrypt(_encode_json_dict(refresh.dict())).decode('utf-8')

        access_payload = finish_token(access_val.dict(), utc_now)
        id_token_payload = finish_token(id_token_val.dict(), utc_now)

        access_token = jwt.encode(access_payload, signing_key, algorithm="EdDSA")
        id_token = jwt.encode(id_token_payload, signing_key, algorithm="EdDSA")

    return id_token, access_token, refresh_token, token_type, access_exp, access_scope


def id_access_tokens(sub, iss, aud_access, aud_id, scope, auth_time, id_nonce):
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


def finish_token(token_val: dict, utc_now: int):
    payload_add = {
        "iat": utc_now,
        "exp": utc_now + access_exp,
    }
    payload = dict(token_val, **payload_add)
    return payload


class BadVerification(Exception):
    pass


def verify_access_token(public_key: str, access_token: str):
    try:
        decoded_payload = jwt.decode(access_token, public_key, algorithms=["EdDSA"], leeway=grace_period,
                                     require=["exp", "aud"], issuer=issuer, audience=[backend_client_id])
    except PyJWTError as e:
        # TODO specify correct errors for return info
        print(e)
        raise BadVerification

    return AccessToken.parse_obj(decoded_payload)
