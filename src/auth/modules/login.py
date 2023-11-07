import opaquepy as opq

from auth.core.error import AuthError
from auth.core.model import PasswordRequest, SavedState, FinishLogin, FlowUser
from auth.core.response import PasswordResponse
from auth.core.util import utc_timestamp
from auth.data.authentication import (
    get_apake_setup,
    get_user_auth_data,
    store_auth_state,
    get_state,
    store_flow_user,
)
from auth.data.context import LoginContext
from store.error import NoDataError
from auth.data.relational.user import UserOps
from store import Store
from store.conn import store_session


async def start_login(
    store: Store, user_ops: UserOps, context: LoginContext, login_start: PasswordRequest
) -> PasswordResponse:
    """Login can be initiated in 2 different flows: the first is the OAuth 2 flow, the second is a simple password
    check flow."""

    login_mail = login_start.email.lower()

    async with store_session(store) as session:
        user_id, scope, password_file, auth_id = await get_user_auth_data(
            context, session, user_ops, login_mail
        )
        apake_setup = await get_apake_setup(context, session)

    # This will only fail if the client message is an invalid OPAQUE protocol message
    response, state = opq.login(
        apake_setup, password_file, login_start.client_request, user_id
    )

    saved_state = SavedState(
        user_id=user_id, user_email=login_mail, scope=scope, state=state
    )

    await store_auth_state(context, store, auth_id, saved_state)

    return PasswordResponse(server_message=response, auth_id=auth_id)


async def finish_login(
    store: Store, context: LoginContext, login_finish: FinishLogin
) -> None:
    finish_email = login_finish.email.lower()
    try:
        saved_state = await get_state(context, store, login_finish.auth_id)
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

    await store_flow_user(context, store, session_key, flow_user)
