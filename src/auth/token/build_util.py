from typing import Any, Type

from auth.core.model import AccessTokenBase, IdTokenBase
from auth.core.util import enc_b64url, enc_dict, dec_dict, dec_b64url
from auth.data.relational.entities import SavedRefreshToken
from auth.data.relational.user import IdUserData


def encode_token_dict(token: dict[str, Any]) -> str:
    return enc_b64url(enc_dict(token))


def finish_payload(token_val: dict[str, Any], utc_now: int, exp: int) -> dict[str, Any]:
    """Add time-based information to static token dict."""
    payload_add = {
        "iat": utc_now,
        "exp": utc_now + exp,
    }
    payload = dict(token_val, **payload_add)
    return payload


def decode_refresh(
    rt: SavedRefreshToken, id_userdata_type: Type[IdUserData]
) -> tuple[AccessTokenBase, IdTokenBase, IdUserData]:
    """Decodes the saved refresh token and validates their structure. id_info_model is generic, because the
    application level decides what it looks like."""
    saved_access_dict = dec_dict(dec_b64url(rt.access_value))
    saved_access = AccessTokenBase.model_validate(saved_access_dict)
    saved_id_token_dict = dec_dict(dec_b64url(rt.id_token_value))
    saved_id_token = IdTokenBase.model_validate(saved_id_token_dict)
    updated_id_userdata = id_userdata_type.from_id_token(saved_id_token_dict)

    return saved_access, saved_id_token, updated_id_userdata


def add_info_to_id(id_token: IdTokenBase, id_userdata: IdUserData) -> dict[str, Any]:
    return id_token.model_dump() | id_userdata.id_info()
