from auth.core.model import SavedRegisterState
from auth.core.util import random_time_hash_hex
from auth.data.context import RegisterContext
from datacontext.context import ContextRegistry
from store import Store
from store.conn import get_kv
from store.kv import store_json


ctx_reg = ContextRegistry()


@ctx_reg.register(RegisterContext)
async def store_auth_register_state(
    store: Store, user_id: str, state: SavedRegisterState
) -> str:
    auth_id = random_time_hash_hex(user_id)

    await store_json(get_kv(store), auth_id, state.model_dump(), expire=1000)

    return auth_id
