import logging

import opaquepy as opq
from fastapi import APIRouter, Response, Request
from fastapi.responses import RedirectResponse
from pydantic import BaseModel

import auth.core.util
from apiserver import data
from auth.core.authorize import oauth_start, oauth_callback
from auth.core.error import RedirectError, AuthError
from apiserver.define import LOGGER_NAME, DEFINE
from apiserver.app.error import ErrorResponse
from apiserver.app.model.models import (
    PasswordResponse,
)
from apiserver.lib.model.entities import SavedState, FlowUser
from apiserver.app.ops.errors import RefreshOperationError
from apiserver.app.ops.header import Authorization
from apiserver.app.ops.tokens import do_refresh, new_token, delete_refresh
from apiserver.app.routers.auth.validations import (
    authorization_validate,
    compare_auth_token_validate,
    refresh_validate,
    TokenRequest,
    TokenResponse,
)
from apiserver.app.routers.helper import require_user
from apiserver.data import NoDataError, Source

router = APIRouter()

port_front = 3000

logger = logging.getLogger(LOGGER_NAME)


class PasswordRequest(BaseModel):
    email: str
    client_request: str


@router.post("/login/start/", response_model=PasswordResponse)
async def start_login(login_start: PasswordRequest, request: Request):
    """Login can be initiated in 2 different flows: the first is the OAuth 2 flow, the second is a simple password
    check flow."""
    dsrc: Source = request.state.dsrc
    login_mail = login_start.email.lower()

    scope = "none"
    async with data.get_conn(dsrc) as conn:
        # We get server setup required for using OPAQUE protocol
        opaque_setup = await data.opaquesetup.get_setup(conn)

        # We start with a fakerecord
        u = await data.user.get_user_by_id(conn, "1_fakerecord")
        password_file = u.password_file
        try:
            ru = await data.user.get_user_by_email(conn, login_mail)
            # If the user exists and has a password set (meaning they are registered), we perform the check with the
            # actual password
            if ru.password_file:
                u = ru
                password_file = ru.password_file
                scope = ru.scope
        except NoDataError:
            # If user or password file does not exist, user, password_file and scope default to the fake record
            pass

    auth_id = auth.core.util.random_time_hash_hex(u.user_id)

    # This will only fail if the client message is an invalid OPAQUE protocol message
    response, state = opq.login(
        opaque_setup, password_file, login_start.client_request, u.user_id
    )

    saved_state = SavedState(
        user_id=u.user_id, user_email=login_mail, scope=scope, state=state
    )

    await data.trs.auth.store_auth_state(dsrc, auth_id, saved_state)

    return PasswordResponse(server_message=response, auth_id=auth_id)


class FinishLogin(BaseModel):
    auth_id: str
    email: str
    client_request: str
    flow_id: str


@router.post("/login/finish/")
async def finish_login(login_finish: FinishLogin, request: Request):
    dsrc: Source = request.state.dsrc
    finish_email = login_finish.email.lower()
    try:
        saved_state = await data.trs.auth.get_state(dsrc, login_finish.auth_id)
    except NoDataError as e:
        logger.debug(e.message)
        reason = "Login not initialized or expired"
        raise ErrorResponse(
            status_code=400,
            err_type="invalid_login",
            err_desc=reason,
            debug_key="no_login_start",
        )
    saved_email = saved_state.user_email.lower()
    if saved_email != finish_email:
        raise ErrorResponse(
            status_code=400,
            err_type="invalid_login",
            err_desc="Incorrect username for this login!",
        )

    session_key = opq.login_finish(login_finish.client_request, saved_state.state)

    utc_now = auth.core.util.utc_timestamp()
    flow_user = FlowUser(
        flow_id=login_finish.flow_id,
        scope=saved_state.scope,
        auth_time=utc_now,
        user_id=saved_state.user_id,
    )

    await data.trs.auth.store_flow_user(dsrc, session_key, flow_user)


@router.get("/oauth/authorize/", status_code=303)
async def oauth_endpoint(
    response_type: str,
    client_id: str,
    redirect_uri: str,
    state: str,
    code_challenge: str,
    code_challenge_method: str,
    nonce: str,
    request: Request,
):
    """This is the authorization endpoint (as in Section 3.1 of the OAuth 2.1 standard). The auth request is validated
    in this step. This initiates the authentication process. This endpoint can only return an error response. If there
    is no error, the /oauth/callback/ endpoint returns the successful response after authentication. Authentication is
    not specified by either OpenID Connect or OAuth 2.1."""
    dsrc: Source = request.state.dsrc

    try:
        redirect = await oauth_start(
            response_type,
            client_id,
            redirect_uri,
            state,
            code_challenge,
            code_challenge_method,
            nonce,
            DEFINE,
            dsrc.store,
        )
    except RedirectError as e:
        return RedirectResponse(e.redirect_uri, status_code=e.code)
    except AuthError as e:
        logger.debug(e.err_desc)
        raise ErrorResponse(400, err_type=e.err_type, err_desc=e.err_desc)

    return RedirectResponse(redirect.url, status_code=redirect.code)


@router.get("/oauth/callback/", status_code=303)
async def oauth_finish(flow_id: str, code: str, response: Response, request: Request):
    """After a successful authentication, this endpoint (the Authorization Endpoint in OAuth 2.1) returns a redirect
    response to the redirect url originally specified in the request. This check has already been performed by the
    /oauth/authorize/ endpoint, as have been all other checks. We do not add the 'iss' parameter (RFC9207) as we assume
    this is the only authorization server the client speaks too."""
    # Prevents cache of value
    response.headers["Cache-Control"] = "no-store"
    response.headers["Pragma"] = "no-cache"

    dsrc: Source = request.state.dsrc

    try:
        redirect = await oauth_callback(flow_id, code, dsrc.store)
    except AuthError as e:
        logger.debug(e.err_desc)
        raise ErrorResponse(400, err_type=e.err_type, err_desc=e.err_desc)

    return RedirectResponse(redirect.url, status_code=redirect.code)


@router.post("/oauth/token/", response_model=TokenResponse)
async def token(token_request: TokenRequest, response: Response, request: Request):
    # Prevents cache, required by OpenID Connect
    response.headers["Cache-Control"] = "no-store"
    response.headers["Pragma"] = "no-cache"

    dsrc: Source = request.state.dsrc
    # We only allow requests meant to be sent from our front end
    # This does not heighten security, only so other clients do not accidentally make requests here
    if token_request.client_id != DEFINE.frontend_client_id:
        reason = "Invalid client ID."
        logger.debug(reason)
        raise ErrorResponse(400, err_type="invalid_client", err_desc=reason)

    token_type = "Bearer"

    # Two available grant types, 'authorization_code' (after login) and 'refresh_token' (when logged in)
    # The first requires a code provided by the OPAQUE login flow
    if token_request.grant_type == "authorization_code":
        logger.debug("authorization_code request")
        # Validate if it contains everything necessary and get flow_user and auth_request
        authorization_validate(token_request)

        try:
            flow_user = await data.trs.auth.pop_flow_user(dsrc, token_request.code)
        except NoDataError as e:
            logger.debug(e.message)
            reason = "Expired or missing auth code"
            raise ErrorResponse(
                400, err_type="invalid_grant", err_desc=reason, debug_key="empty_flow"
            )

        try:
            auth_request = await data.trs.auth.get_auth_request(dsrc, flow_user.flow_id)
        except NoDataError as e:
            # TODO maybe check auth time just in case
            logger.debug(e.message)
            reason = "Expired or missing auth request"
            raise ErrorResponse(400, err_type="invalid_grant", err_desc=reason)

        # Validate if auth_request corresponds to token_request
        compare_auth_token_validate(token_request, auth_request)

        auth_time = flow_user.auth_time
        id_nonce = auth_request.nonce
        token_user_id = flow_user.user_id

        token_scope = flow_user.scope
        id_token, access, refresh, exp, returned_scope = await new_token(
            dsrc, token_user_id, token_scope, auth_time, id_nonce
        )

    elif token_request.grant_type == "refresh_token":
        logger.debug("refresh_token request")
        refresh_validate(token_request)

        old_refresh = token_request.refresh_token

        try:
            (
                id_token,
                access,
                refresh,
                exp,
                returned_scope,
                token_user_id,
            ) = await do_refresh(dsrc, old_refresh)
        except RefreshOperationError as e:
            error_desc = "Invalid refresh_token!"
            logger.debug(f"{str(e)}: {error_desc}")
            raise ErrorResponse(
                400, err_type="invalid_grant", err_desc="Invalid refresh_token!"
            )

    else:
        reason = (
            "Only 'refresh_token' and 'authorization_code' grant types are available."
        )
        logger.debug(f"{reason} Used: {token_request.grant_type}")
        raise ErrorResponse(400, err_type="unsupported_grant_type", err_desc=reason)

    logger.info(f"Token request granted for {token_user_id}")
    return TokenResponse(
        id_token=id_token,
        access_token=access,
        refresh_token=refresh,
        token_type=token_type,
        expires_in=exp,
        scope=returned_scope,
    )


@router.get("/oauth/ping/")
async def get_users(user: str, request: Request, authorization: Authorization):
    dsrc: Source = request.state.dsrc
    acc = await require_user(authorization, dsrc, user)
    return acc.exp


class LogoutRequest(BaseModel):
    refresh_token: str


@router.post("/logout/delete/")
async def delete_token(logout: LogoutRequest, request: Request):
    dsrc: Source = request.state.dsrc
    await delete_refresh(dsrc, logout.refresh_token)
