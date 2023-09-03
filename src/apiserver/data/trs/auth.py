from store.kv import get_json
from apiserver.data import Source, get_kv
from store.error import NoDataError
from apiserver.lib.model.entities import AuthRequest


async def get_auth_request(dsrc: Source, flow_id: str) -> AuthRequest:
    auth_req_dict: dict = await get_json(get_kv(dsrc), flow_id)
    if auth_req_dict is None:
        raise NoDataError(
            "Auth request does not exist or expired.", "auth_request_empty"
        )
    return AuthRequest.model_validate(auth_req_dict)
