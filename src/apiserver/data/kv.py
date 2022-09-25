from typing import Optional

from apiserver.define import email_expiration
from apiserver.define.request import FlowUser, AuthRequest, SavedState, SavedRegisterState, SignupRequest
from apiserver.data.source import NoDataError
from apiserver.data import Source, DataError
from apiserver.kv import store_json, get_json, get_kv, store_kv, pop_json


def kv_is_init(dsrc: Source):
    if dsrc.gateway.kv is None:
        raise DataError("Database not initialized!", "no_db_init")
    else:
        return dsrc.gateway.kv


async def pop_flow_user(dsrc: Source, authorization_code: str):
    flow_user_dict = await pop_json(kv_is_init(dsrc), authorization_code)
    if flow_user_dict is None:
        raise NoDataError("Flow user does not exist or expired.", "flow_user_empty")
    return FlowUser.parse_obj(flow_user_dict)


async def get_auth_request(dsrc: Source, flow_id: str):
    auth_req_dict = await get_json(kv_is_init(dsrc), flow_id)
    if auth_req_dict is None:
        raise NoDataError("Auth request does not exist or expired.", "auth_request_empty")
    return AuthRequest.parse_obj(auth_req_dict)


async def store_auth_register_state(dsrc: Source, auth_id: str, state: SavedRegisterState):
    await store_json(kv_is_init(dsrc), auth_id, state.dict(), expire=1000)


async def store_auth_state(dsrc: Source, auth_id: str, state: SavedState):
    await store_json(kv_is_init(dsrc), auth_id, state.dict(), expire=1000)


async def get_state(dsrc: Source, auth_id: str):
    state_dict = await get_json(kv_is_init(dsrc), auth_id)
    if state_dict is None:
        raise NoDataError("State does not exist or expired.", "saved_state_empty")
    return SavedState.parse_obj(state_dict)


async def get_register_state(dsrc: Source, auth_id: str):
    state_dict = await get_json(kv_is_init(dsrc), auth_id)
    if state_dict is None:
        raise NoDataError("State does not exist or expired.", "saved_state_empty")
    return SavedRegisterState.parse_obj(state_dict)


async def store_flow_user(dsrc: Source, session_key: str, flow_user: FlowUser):
    await store_json(kv_is_init(dsrc), session_key, flow_user.dict(), expire=60)


async def store_auth_request(dsrc: Source, flow_id: str, auth_request: AuthRequest):
    await store_json(kv_is_init(dsrc), flow_id, auth_request.dict(), expire=1000)


async def store_email_confirmation(dsrc: Source, confirm_id: str, signup: SignupRequest):
    await store_json(kv_is_init(dsrc), confirm_id, signup.dict(), expire=email_expiration)


async def get_email_confirmation(dsrc: Source, confirm_id: str) -> SignupRequest:
    signup_dict = await get_json(kv_is_init(dsrc), confirm_id)
    if signup_dict is None:
        raise NoDataError("Confirmation ID does not exist or expired.", "saved_confirm_empty")
    return SignupRequest.parse_obj(signup_dict)


async def store_string(dsrc: Source, key: str, value: str, expire: int):
    await store_kv(kv_is_init(dsrc), key, value, expire)


async def get_string(dsrc: Source, key: str) -> str:
    value = await get_kv(kv_is_init(dsrc), key)
    if value is None:
        raise NoDataError("String for this key does not exist or expired.", "saved_str_empty")
    try:
        return value.decode()
    except UnicodeEncodeError:
        raise DataError("Data is not of unicode string type.", "bad_str_encode")
