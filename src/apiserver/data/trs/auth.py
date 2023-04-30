from apiserver.data import Source, NoDataError, get_kv
from apiserver.data.kv import get_json, store_json, pop_json
from apiserver.lib.model.entities import AuthRequest, SavedState, FlowUser


async def get_auth_request(dsrc: Source, flow_id: str) -> AuthRequest:
    auth_req_dict: dict = await get_json(get_kv(dsrc), flow_id)
    if auth_req_dict is None:
        raise NoDataError(
            "Auth request does not exist or expired.", "auth_request_empty"
        )
    return AuthRequest.parse_obj(auth_req_dict)


async def store_auth_request(dsrc: Source, flow_id: str, auth_request: AuthRequest):
    await store_json(get_kv(dsrc), flow_id, auth_request.dict(), expire=1000)


async def store_auth_state(dsrc: Source, auth_id: str, state: SavedState):
    await store_json(get_kv(dsrc), auth_id, state.dict(), expire=60)


async def get_state(dsrc: Source, auth_id: str) -> SavedState:
    state_dict: dict = await get_json(get_kv(dsrc), auth_id)
    if state_dict is None:
        raise NoDataError("State does not exist or expired.", "saved_state_empty")
    return SavedState.parse_obj(state_dict)


async def pop_flow_user(dsrc: Source, authorization_code: str) -> FlowUser:
    flow_user_dict: dict = await pop_json(get_kv(dsrc), authorization_code)
    if flow_user_dict is None:
        raise NoDataError("Flow user does not exist or expired.", "flow_user_empty")
    return FlowUser.parse_obj(flow_user_dict)


async def store_flow_user(dsrc: Source, session_key: str, flow_user: FlowUser):
    await store_json(get_kv(dsrc), session_key, flow_user.dict(), expire=60)
