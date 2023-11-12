from loguru import logger
from auth.core.error import AuthError, RefreshOperationError
from auth.core.model import (
    CodeGrantRequest,
    Tokens,
    TokenResponse,
    KeyState,
    TokenRequest,
)
from auth.data.authentication import pop_flow_user
from auth.data.authorize import get_auth_request
from auth.data.context import TokenContext
from store.error import NoDataError
from auth.data.relational.ops import RelationOps
from auth.define import Define
from auth.modules.token.create import new_token, do_refresh
from auth.validate.token import (
    authorization_validate,
    compare_auth_token_validate,
    refresh_validate,
)
from store import Store


async def process_token_request(
    store: Store,
    define: Define,
    ops: RelationOps,
    context: TokenContext,
    key_state: KeyState,
    token_request: TokenRequest,
) -> TokenResponse:
    # We only allow requests meant to be sent from our front end
    # This does not heighten security, only so other clients do not accidentally make requests here
    if token_request.client_id != define.frontend_client_id:
        reason = "Invalid client ID."
        raise AuthError(err_type="invalid_client", err_desc=reason)

    token_type = "Bearer"

    # Two available grant types, 'authorization_code' (after login) and 'refresh_token' (when logged in)
    # The first requires a code provided by the OPAQUE login flow
    if token_request.grant_type == "authorization_code":
        # THROWS AuthError
        code_grant_request = authorization_validate(token_request)
        # Verify authorization code
        # THROWS AuthError, UnexpectedError
        tokens = await auth_code_grant(
            store, define, ops, context, key_state, code_grant_request
        )

    elif token_request.grant_type == "refresh_token":
        logger.debug("refresh_token request")
        old_refresh = refresh_validate(token_request)
        # Verify old refresh token
        tokens = await request_token_grant(store, ops, context, key_state, old_refresh)

    else:
        reason = (
            "Only 'refresh_token' and 'authorization_code' grant types are available."
        )
        logger.debug(f"{reason} Used: {token_request.grant_type}")
        raise AuthError(err_type="unsupported_grant_type", err_desc=reason)

    return TokenResponse(
        id_token=tokens.id,
        access_token=tokens.acc,
        refresh_token=tokens.refr,
        token_type=token_type,
        expires_in=tokens.exp,
        scope=tokens.scope,
    )


async def auth_code_grant(
    store: Store,
    define: Define,
    ops: RelationOps,
    context: TokenContext,
    key_state: KeyState,
    code_grant_request: CodeGrantRequest,
) -> Tokens:
    # Get flow_user and auth_request
    try:
        flow_user = await pop_flow_user(context, store, code_grant_request.code)
    except NoDataError:
        reason = "Expired or missing auth code"
        raise AuthError(
            err_type="invalid_grant", err_desc=reason, debug_key="empty_flow"
        )

    try:
        auth_request = await get_auth_request(context, store, flow_user.flow_id)
    except NoDataError:
        # TODO maybe check auth time just in case
        reason = "Expired or missing auth request"
        raise AuthError(err_type="invalid_grant", err_desc=reason)

    # Validate if auth_request corresponds to token_request
    # THROWS AuthError if it does not correspond
    compare_auth_token_validate(code_grant_request, auth_request)

    auth_time = flow_user.auth_time
    id_nonce = auth_request.nonce
    token_user_id = flow_user.user_id

    token_scope = flow_user.scope
    # GETS keys, GETS id_info
    # Creates new tokens
    # SAVES refresh_token
    return await new_token(
        store,
        define,
        ops,
        context,
        key_state,
        token_user_id,
        token_scope,
        auth_time,
        id_nonce,
    )


async def request_token_grant(
    store: Store,
    ops: RelationOps,
    context: TokenContext,
    key_state: KeyState,
    old_refresh: str,
) -> Tokens:
    try:
        return await do_refresh(store, ops, context, key_state, old_refresh)
    except RefreshOperationError as e:
        error_desc = "Invalid refresh_token!"
        logger.debug(f"{e!s}: {error_desc}")
        raise AuthError(err_type="invalid_grant", err_desc=error_desc)
