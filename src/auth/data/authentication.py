from store import Store
from store.conn import get_conn, get_kv
from store.kv import store_json, get_json, pop_json

from auth.core.model import SavedState, FlowUser
from auth.core.util import random_time_hash_hex
from store.error import NoDataError
from auth.data.schemad.user import UserOps
from auth.data.schemad.opaque import get_setup


async def get_apake_setup(store: Store):
    """We get server setup required for using OPAQUE protocol (which is an aPAKE)."""
    async with get_conn(store) as conn:
        return await get_setup(conn)


async def get_user_auth_data(store: Store, user_ops: UserOps, login_mail: str):
    scope = "none"
    async with get_conn(store) as conn:
        # We start with a fakerecord
        u = await user_ops.get_user_by_id(conn, "1_fakerecord")
        password_file = u.password_file
        try:
            ru = await user_ops.get_user_by_email(conn, login_mail)
            # If the user exists and has a password set (meaning they are registered), we perform the check with the
            # actual password
            if ru.password_file:
                u = ru
                password_file = ru.password_file
                scope = ru.scope
        except NoDataError:
            # If user or password file does not exist, user, password_file and scope default to the fake record
            pass

    auth_id = random_time_hash_hex(u.user_id)

    return u, scope, password_file, auth_id


async def store_auth_state(store: Store, auth_id: str, state: SavedState):
    await store_json(get_kv(store), auth_id, state.model_dump(), expire=60)


async def get_state(store: Store, auth_id: str) -> SavedState:
    state_dict: dict = await get_json(get_kv(store), auth_id)
    if state_dict is None:
        raise NoDataError("State does not exist or expired.", "saved_state_empty")
    return SavedState.model_validate(state_dict)


async def pop_flow_user(store: Store, authorization_code: str) -> FlowUser:
    flow_user_dict: dict = await pop_json(get_kv(store), authorization_code)
    if flow_user_dict is None:
        raise NoDataError("Flow user does not exist or expired.", "flow_user_empty")
    return FlowUser.model_validate(flow_user_dict)


async def store_flow_user(store: Store, session_key: str, flow_user: FlowUser):
    await store_json(get_kv(store), session_key, flow_user.model_dump(), expire=60)
