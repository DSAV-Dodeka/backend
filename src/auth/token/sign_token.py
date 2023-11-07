from typing import Any

from auth.core.model import AccessTokenBase, IdTokenBase
from auth.data.relational.user import IdUserData
from auth.hazmat.sign_dict import sign_dict
from auth.hazmat.structs import PEMPrivateKey
from auth.token.build_util import finish_payload, add_info_to_id


def _finish_sign(
    private_key: PEMPrivateKey,
    unfinished_token_val: dict[str, Any],
    utc_now: int,
    exp: int,
) -> str:
    finished_payload = finish_payload(unfinished_token_val, utc_now, exp)
    return sign_dict(private_key, finished_payload)


def sign_access_token(
    private_key: PEMPrivateKey,
    access_token_data: AccessTokenBase,
    utc_now: int,
    exp: int,
) -> str:
    return _finish_sign(private_key, access_token_data.model_dump(), utc_now, exp)


def sign_id_token(
    private_key: PEMPrivateKey,
    id_token_data: IdTokenBase,
    id_userdata: IdUserData,
    utc_now: int,
    exp: int,
) -> str:
    unfinished_token = add_info_to_id(id_token_data, id_userdata)
    return _finish_sign(private_key, unfinished_token, utc_now, exp)
