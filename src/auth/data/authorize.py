from auth.core.model import AuthRequest
from auth.core.util import random_time_hash_hex
from auth.data.context import AuthorizeContext, TokenContext
from datacontext.context import ContextRegistry
from store.error import NoDataError
from store import Store
from store.kv import get_json, store_json
from store.conn import get_kv


ctx_reg = ContextRegistry()


@ctx_reg.register_multiple([TokenContext, AuthorizeContext])
async def get_auth_request(store: Store, flow_id: str) -> AuthRequest:
    auth_req_dict = await get_json(get_kv(store), flow_id)
    if auth_req_dict is None:
        raise NoDataError(
            "Auth request does not exist or expired.", "auth_request_empty"
        )
    return AuthRequest.model_validate(auth_req_dict)


@ctx_reg.register(AuthorizeContext)
async def store_auth_request(store: Store, auth_request: AuthRequest) -> str:
    flow_id = random_time_hash_hex()

    await store_json(get_kv(store), flow_id, auth_request.model_dump(), expire=1000)

    return flow_id
