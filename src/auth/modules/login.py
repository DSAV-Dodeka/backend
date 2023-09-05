import opaquepy as opq

from auth import data
from auth.core.error import AuthError
from auth.core.model import PasswordRequest, SavedState, FinishLogin, FlowUser
from auth.core.response import PasswordResponse
from auth.core.util import utc_timestamp
from store.error import NoDataError
from auth.data.schemad.user import UserOps
from store import Store
from store.conn import store_session


async def start_login(store: Store, user_ops: UserOps, login_start: PasswordRequest):
    """Login can be initiated in 2 different flows: the first is the OAuth 2 flow, the second is a simple password
    check flow."""

    login_mail = login_start.email.lower()

    async with store_session(store) as session:
        u, scope, password_file, auth_id = await data.authentication.get_user_auth_data(
            session, user_ops, login_mail
        )
        apake_setup = await data.authentication.get_apake_setup(session)

    # This will only fail if the client message is an invalid OPAQUE protocol message
    response, state = opq.login(
        apake_setup, password_file, login_start.client_request, u.user_id
    )

    saved_state = SavedState(
        user_id=u.user_id, user_email=login_mail, scope=scope, state=state
    )

    await data.authentication.store_auth_state(store, auth_id, saved_state)

    return PasswordResponse(server_message=response, auth_id=auth_id)


async def finish_login(store: Store, login_finish: FinishLogin):
    finish_email = login_finish.email.lower()
    try:
        saved_state = await data.authentication.get_state(store, login_finish.auth_id)
    except NoDataError:
        reason = "Login not initialized or expired"
        raise AuthError(
            err_type="invalid_request",
            err_desc=reason,
            debug_key="no_login_start",
        )
    saved_email = saved_state.user_email.lower()
    if saved_email != finish_email:
        raise AuthError(
            err_type="invalid_request",
            err_desc="Incorrect username for this login!",
        )

    session_key = opq.login_finish(login_finish.client_request, saved_state.state)

    utc_now = utc_timestamp()
    flow_user = FlowUser(
        flow_id=login_finish.flow_id,
        scope=saved_state.scope,
        auth_time=utc_now,
        user_id=saved_state.user_id,
    )

    await data.authentication.store_flow_user(store, session_key, flow_user)
