from typing import Type

from auth.core.model import AccessTokenBase, IdTokenBase, IdInfo
from auth.core.util import enc_b64url, enc_dict, dec_dict, dec_b64url
from auth.data.schemad.entities import SavedRefreshToken


def encode_token_dict(token: dict):
    return enc_b64url(enc_dict(token))


def finish_payload(token_val: dict, utc_now: int, exp: int):
    """Add time-based information to static token dict."""
    payload_add = {
        "iat": utc_now,
        "exp": utc_now + exp,
    }
    payload = dict(token_val, **payload_add)
    return payload


def decode_refresh(rt: SavedRefreshToken, id_info_model: Type[IdInfo]):
    saved_access_dict = dec_dict(dec_b64url(rt.access_value))
    saved_access = AccessTokenBase.model_validate(saved_access_dict)
    saved_id_token_dict = dec_dict(dec_b64url(rt.id_token_value))
    saved_id_token = IdTokenBase.model_validate(saved_id_token_dict)
    id_info = id_info_model.model_validate(saved_id_token_dict)

    return saved_access, saved_id_token, id_info


def add_info_to_id(id_token: IdTokenBase, id_info: IdInfo):
    """This function is necessary because IdInfo is determined at the application-level, so we do not know exactly
    which model."""
    return id_token.model_dump() | id_info.model_dump()
