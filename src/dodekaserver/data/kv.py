from dodekaserver.data.source import NoDataError
from dodekaserver.define import FlowUser, AuthRequest, SavedState
from dodekaserver.data import Source, DataError
from dodekaserver.kv import store_json, get_json, get_kv, store_kv


async def get_flow_user(dsrc: Source, authorization_code: str):
    flow_user_dict = get_json(dsrc.gateway.kv, authorization_code)
    if flow_user_dict is None:
        raise NoDataError("Flow user does not exist or expired.", "flow_user_empty")
    return FlowUser.parse_obj(flow_user_dict)


async def get_auth_request(dsrc: Source, flow_id: str):
    auth_req_dict = get_json(dsrc.gateway.kv, flow_id)
    if auth_req_dict is None:
        raise NoDataError("Auth request does not exist or expired.", "auth_request_empty")
    return AuthRequest.parse_obj(auth_req_dict)


async def store_auth_state(dsrc: Source, auth_id: str, state: SavedState):
    store_json(dsrc.gateway.kv, auth_id, state.dict(), expire=1000)


async def get_state(dsrc: Source, auth_id: str):
    state_dict = get_json(dsrc.gateway.kv, auth_id)
    if state_dict is None:
        raise NoDataError("State does not exist or expired.", "saved_state_empty")
    return SavedState.parse_obj(state_dict)


async def store_flow_user(dsrc: Source, session_key: str, flow_user: FlowUser):
    store_json(dsrc.gateway.kv, session_key, flow_user.dict(), expire=60)


async def store_auth_request(dsrc: Source, flow_id: str, auth_request: AuthRequest):
    store_json(dsrc.gateway.kv, flow_id, auth_request.dict(), expire=1000)
