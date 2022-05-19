from dodekaserver.define import FlowUser, AuthRequest
from dodekaserver.data import Source, DataError
from dodekaserver.kv import store_json, get_json, get_kv, store_kv


async def get_flow_user(dsrc: Source, authorization_code: str):
    flow_user_dict = get_json(dsrc.gateway.kv, authorization_code)
    if flow_user_dict is None:
        raise DataError("Flow user does not exist or expired.", "flow_user_empty")
    return FlowUser.parse_obj(flow_user_dict)


async def get_auth_request(dsrc: Source, flow_id: str):
    auth_req_dict = get_json(dsrc.gateway.kv, flow_id)
    if auth_req_dict is None:
        raise DataError("Auth request does not exist or expired.", "auth_request_empty")
    return AuthRequest.parse_obj(auth_req_dict)
