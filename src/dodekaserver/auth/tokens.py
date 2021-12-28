import secrets
import hashlib
import hmac
import json
from secrets import token_urlsafe
from cryptography.fernet import Fernet
from datetime import datetime

import jwt

from dodekaserver.utilities import add_base64_padding, encb64url_str, decb64url_str
import dodekaserver.data as data
from dodekaserver.data.entities import SavedRefreshToken, RefreshToken
from dodekaserver.data import Source


__all__ = ['create_refresh_access_pair', 'create_id_token']


id_exp = 10*60*60  # 10 hours
access_exp = 1*60*60  # 1 hour
refresh_exp = 30*24*60*60 # 1 month


def _encode_json_dict(dct: dict) -> bytes:
    return json.dumps(dct).encode('utf-8')


def _decode_json_dict(encoded: bytes) -> dict:
    return json.loads(encoded.decode('utf-8'))


async def create_id_token(user_usph: str, auth_time: int, nonce: str, dsrc: Source = None, private_key=None):
    utc_now = int(datetime.utcnow().timestamp())
    if auth_time == -1:
        auth_time = utc_now
    elif auth_time > utc_now or auth_time < 1640690242:
        # Prevent weird timestamps
        # The literal timestamp is 28/12/21
        raise ValueError("Invalid timestamp!")

    payload = {
        "sub": user_usph,
        "iss": "https://dsavdodeka.nl/auth",
        "aud": "dodekaweb_client",
        "iat": utc_now,
        "exp": utc_now + id_exp,
        "auth_time": auth_time,
        "nonce": nonce
    }
    if dsrc is not None:
        private_key = await data.key.get_token_private(dsrc)
    return jwt.encode(payload, private_key, algorithm="EdDSA")


async def create_refresh_access_pair(dsrc: Source, user_usph: str = None, scope: str = None, refresh_token: str = None):
    # ENSURE scope is validated by the server first, do not pass directly from client

    symmetric_key = await data.key.get_refresh_symmetric(dsrc)
    padded_symmetric_key = add_base64_padding(symmetric_key)
    fernet = Fernet(padded_symmetric_key)

    if refresh_token is not None:
        # expects base64url-encoded binary
        decrypted = fernet.decrypt(refresh_token.encode('utf-8'))
        refresh_dict = _decode_json_dict(decrypted)
        print(refresh_dict)
    else:
        assert user_usph is not None
        assert scope is not None

        utc_now = int(datetime.utcnow().timestamp())

        refresh_access_val = {
            "sub": user_usph,
            "iss": "https://dsavdodeka.nl/auth",
            "aud": ["dodekaweb_client", "dodekabackend_client"],
            "scope": scope,
        }

        access_val_encoded = encb64url_str(_encode_json_dict(refresh_access_val))
        family_id = secrets.token_urlsafe(16)
        refresh_save = SavedRefreshToken(family_id=family_id, access_value=access_val_encoded,
                                         exp=utc_now + refresh_exp)
        refresh_id = await data.refreshtoken.refresh_save(dsrc, refresh_save)
        refresh = RefreshToken(id=refresh_id, family_id=refresh_save.family_id)
        # add iat?

        # the bytes are base64url-encoded
        refresh_token = fernet.encrypt(_encode_json_dict(refresh.dict())).decode('utf-8')

        # TODO make this opaque
        payload_add = {
            "iat": utc_now,
            "exp": utc_now + access_exp,
        }
        payload = dict(refresh_access_val, **payload_add)

        private_key = await data.key.get_token_private(dsrc)
        access_token = jwt.encode(payload, private_key, algorithm="EdDSA")
        return access_token, refresh_token

