from auth.core.model import SavedRegisterState
from store import Store
from store.conn import get_kv
from store.kv import store_json


async def store_auth_register_state(
    store: Store, auth_id: str, state: SavedRegisterState
):
    await store_json(get_kv(store), auth_id, state.model_dump(), expire=1000)
