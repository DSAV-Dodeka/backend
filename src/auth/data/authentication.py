from auth.core.model import SavedState, FlowUser
from auth.core.util import random_time_hash_hex
from auth.data.context import RegisterContext, LoginContext, TokenContext
from auth.data.relational.opaque import get_setup
from auth.data.relational.user import UserOps
from datacontext.context import ContextRegistry
from store import Store
from store.conn import get_conn, get_kv
from store.error import NoDataError
from store.kv import store_json, get_json, pop_json

ctx_reg = ContextRegistry()


@ctx_reg.register_multiple([RegisterContext, LoginContext])
async def get_apake_setup(store: Store) -> str:
    """We get server setup required for using OPAQUE protocol (which is an aPAKE)."""
    async with get_conn(store) as conn:
        return await get_setup(conn)


@ctx_reg.register(LoginContext)
async def get_user_auth_data(
    store: Store, user_ops: UserOps, login_mail: str
) -> tuple[str, str, str, str]:
    scope = "none"
    async with get_conn(store) as conn:
        # We start with a fakerecord
        u = await user_ops.get_user_by_id(conn, "1_fakerecord")
        user_id = u.user_id
        password_file = u.password_file
        try:
            ru = await user_ops.get_user_by_email(conn, login_mail)
            # If the user exists and has a password set (meaning they are registered), we perform the check with the
            # actual password
            if ru.password_file:
                user_id = ru.user_id
                password_file = ru.password_file
                scope = ru.scope
        except NoDataError:
            # If user or password file does not exist, user, password_file and scope default to the fake record
            pass

    auth_id = random_time_hash_hex(user_id)
    return user_id, scope, password_file, auth_id


@ctx_reg.register(LoginContext)
async def store_auth_state(store: Store, auth_id: str, state: SavedState) -> None:
    await store_json(get_kv(store), auth_id, state.model_dump(), expire=60)


@ctx_reg.register(LoginContext)
async def get_state(store: Store, auth_id: str) -> SavedState:
    state_dict = await get_json(get_kv(store), auth_id)
    if state_dict is None:
        raise NoDataError("State does not exist or expired.", "saved_state_empty")
    return SavedState.model_validate(state_dict)


@ctx_reg.register_multiple([TokenContext, LoginContext])
async def pop_flow_user(store: Store, authorization_code: str) -> FlowUser:
    flow_user_dict = await pop_json(get_kv(store), authorization_code)
    if flow_user_dict is None:
        raise NoDataError("Flow user does not exist or expired.", "flow_user_empty")
    return FlowUser.model_validate(flow_user_dict)


@ctx_reg.register(LoginContext)
async def store_flow_user(store: Store, session_key: str, flow_user: FlowUser) -> None:
    await store_json(get_kv(store), session_key, flow_user.model_dump(), expire=60)
