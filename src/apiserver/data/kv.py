from typing import Optional

from redis.asyncio import Redis

from apiserver.data import Source, DataError
from apiserver.data.source import NoDataError
from apiserver.define import email_expiration
from apiserver.define.entities import PEMKey, A256GCMKey, JWKSet
from apiserver.define.reqres import (
    FlowUser,
    AuthRequest,
    SavedState,
    SavedRegisterState,
    SignupRequest,
    UpdateEmailState,
)
from apiserver.kv import (
    store_json,
    get_json,
    get_kv,
    store_kv,
    pop_json,
    store_json_perm,
    store_json_multi,
)
from apiserver.kv.kv import store_kv_perm


def kv_is_init(dsrc: Source) -> Redis:
    if dsrc.gateway.kv is None:
        raise DataError("Database not initialized!", "no_db_init")
    else:
        return dsrc.gateway.kv


async def pop_flow_user(dsrc: Source, authorization_code: str) -> FlowUser:
    flow_user_dict: dict = await pop_json(kv_is_init(dsrc), authorization_code)
    if flow_user_dict is None:
        raise NoDataError("Flow user does not exist or expired.", "flow_user_empty")
    return FlowUser.parse_obj(flow_user_dict)


async def get_auth_request(dsrc: Source, flow_id: str) -> AuthRequest:
    auth_req_dict: dict = await get_json(kv_is_init(dsrc), flow_id)
    if auth_req_dict is None:
        raise NoDataError(
            "Auth request does not exist or expired.", "auth_request_empty"
        )
    return AuthRequest.parse_obj(auth_req_dict)


async def store_auth_register_state(
    dsrc: Source, auth_id: str, state: SavedRegisterState
):
    await store_json(kv_is_init(dsrc), auth_id, state.dict(), expire=1000)


async def store_auth_state(dsrc: Source, auth_id: str, state: SavedState):
    await store_json(kv_is_init(dsrc), auth_id, state.dict(), expire=60)


async def get_state(dsrc: Source, auth_id: str) -> SavedState:
    state_dict: dict = await get_json(kv_is_init(dsrc), auth_id)
    if state_dict is None:
        raise NoDataError("State does not exist or expired.", "saved_state_empty")
    return SavedState.parse_obj(state_dict)


async def get_register_state(dsrc: Source, auth_id: str) -> SavedRegisterState:
    state_dict: dict = await get_json(kv_is_init(dsrc), auth_id)
    if state_dict is None:
        raise NoDataError("State does not exist or expired.", "saved_state_empty")
    return SavedRegisterState.parse_obj(state_dict)


async def store_flow_user(dsrc: Source, session_key: str, flow_user: FlowUser):
    await store_json(kv_is_init(dsrc), session_key, flow_user.dict(), expire=60)


async def store_auth_request(dsrc: Source, flow_id: str, auth_request: AuthRequest):
    await store_json(kv_is_init(dsrc), flow_id, auth_request.dict(), expire=1000)


async def store_email_confirmation(
    dsrc: Source, confirm_id: str, signup: SignupRequest
):
    await store_json(
        kv_is_init(dsrc), confirm_id, signup.dict(), expire=email_expiration
    )


async def get_email_confirmation(dsrc: Source, confirm_id: str) -> SignupRequest:
    signup_dict: dict = await get_json(kv_is_init(dsrc), confirm_id)
    if signup_dict is None:
        raise NoDataError(
            "Confirmation ID does not exist or expired.", "saved_confirm_empty"
        )
    return SignupRequest.parse_obj(signup_dict)


async def store_update_email(
    dsrc: Source, flow_id: str, update_email: UpdateEmailState
):
    await store_json(kv_is_init(dsrc), flow_id, update_email.dict(), expire=1000)


async def get_update_email(dsrc: Source, flow_id: str) -> UpdateEmailState:
    email_dict: dict = await pop_json(kv_is_init(dsrc), flow_id)
    if email_dict is None:
        raise NoDataError(
            "Flow ID does not exist or expired.", "saved_email_update_empty"
        )
    return UpdateEmailState.parse_obj(email_dict)


async def store_string(dsrc: Source, key: str, value: str, expire: int = 1000):
    if expire == -1:
        await store_kv_perm(kv_is_init(dsrc), key, value)
    else:
        await store_kv(kv_is_init(dsrc), key, value, expire)


async def get_string(dsrc: Source, key: str) -> str:
    value = await get_kv(kv_is_init(dsrc), key)
    if value is None:
        raise NoDataError(
            "String for this key does not exist or expired.", "saved_str_empty"
        )
    try:
        return value.decode()
    except UnicodeEncodeError:
        raise DataError("Data is not of unicode string type.", "bad_str_encode")


async def store_pem_keys(dsrc: Source, keys: list[PEMKey]):
    keys_to_store = {f"{key.kid}-pem": key.dict() for key in keys}

    await store_json_multi(kv_is_init(dsrc), keys_to_store)


async def store_symmetric_keys(dsrc: Source, keys: list[A256GCMKey]):
    keys_to_store = {key.kid: key.dict() for key in keys}

    await store_json_multi(kv_is_init(dsrc), keys_to_store)


async def store_jwks(dsrc: Source, value: JWKSet):
    await store_json_perm(kv_is_init(dsrc), "jwk_set", value.dict())


async def get_jwks(dsrc: Source, kid: str):
    jwks_dict: dict = await get_json(kv_is_init(dsrc), kid)
    if jwks_dict is None:
        raise NoDataError("JWK does not exist or expired.", "jwk_empty")
    return JWKSet.parse_obj(jwks_dict)


async def get_pem_key(dsrc: Source, kid: str) -> PEMKey:
    pem_dict: dict = await get_json(kv_is_init(dsrc), f"{kid}-pem")
    if pem_dict is None:
        raise NoDataError("PEM key does not exist.", "pem_key_empty")
    return PEMKey.parse_obj(pem_dict)


async def get_symmetric_key(dsrc: Source, kid: str) -> A256GCMKey:
    symmetric_dict: dict = await get_json(kv_is_init(dsrc), kid)
    if symmetric_dict is None:
        raise NoDataError("JWK does not exist or expired.", "jwk_empty")
    return A256GCMKey.parse_obj(symmetric_dict)


async def set_startup_lock(dsrc: Source, value="locked"):
    await store_string(dsrc, "startup_lock", value, 25)


async def startup_is_locked(dsrc: Source) -> Optional[bool]:
    try:
        lock = await get_string(dsrc, "startup_lock")
        return lock == "locked"
    except NoDataError:
        return None
