import hashlib
import logging
from urllib.parse import urlencode

import opaquepy as opq
from fastapi import APIRouter, status, Response, Request, Security
from fastapi.responses import RedirectResponse
from pydantic import ValidationError

import apiserver.data as data
import apiserver.utilities as util
from apiserver.auth.header import auth_header
from apiserver.auth.tokens import InvalidRefresh
from apiserver.auth.tokens_data import do_refresh, new_token, delete_refresh
from apiserver.data import NoDataError, Source
from apiserver.define import frontend_client_id, credentials_url, LOGGER_NAME
from apiserver.define.reqres import (
    ErrorResponse,
    PasswordResponse,
    PasswordRequest,
    SavedState,
    FinishLogin,
    AuthRequest,
    TokenResponse,
    TokenRequest,
    FlowUser,
    LogoutRequest,
)
from apiserver.routers.helper import require_user

router = APIRouter()

port_front = 3000

logger = logging.getLogger(LOGGER_NAME)


@router.post("/login/start/", response_model=PasswordResponse)
async def start_login(login_start: PasswordRequest, request: Request):
    """Login can be initiated in 2 different flows: the first is the OAuth 2 flow, the second is a simple password
    check flow."""
    dsrc: Source = request.app.state.dsrc
    login_mail = login_start.email.lower()

    scope = "none"
    async with data.get_conn(dsrc) as conn:
        # We get server setup required for using OPAQUE protocol
        opaque_setup = await data.opaquesetup.get_setup(dsrc, conn)

        # We start with a fakerecord
        u = await data.user.get_user_by_id(dsrc, conn, "1_fakerecord")
        password_file = u.password_file
        try:
            ru = await data.user.get_user_by_email(dsrc, conn, login_mail)
            # If the user exists and has a password set (meaning they are registered), we perform the check with the
            # actual password
            if ru.password_file:
                u = ru
                password_file = ru.password_file
                scope = ru.scope
        except NoDataError:
            # If user or password file does not exist, user, password_file and scope default to the fake record
            pass

    auth_id = util.random_time_hash_hex(u.user_id)

    # This will only fail if the client message is an invalid OPAQUE protocol message
    response, state = opq.login(
        opaque_setup, password_file, login_start.client_request, u.user_id
    )

    saved_state = SavedState(
        user_id=u.user_id, user_email=login_mail, scope=scope, state=state
    )

    await data.kv.store_auth_state(dsrc, auth_id, saved_state)

    return PasswordResponse(server_message=response, auth_id=auth_id)


@router.post("/login/finish/")
async def finish_login(login_finish: FinishLogin, request: Request):
    dsrc: Source = request.app.state.dsrc
    finish_email = login_finish.email.lower()
    try:
        saved_state = await data.kv.get_state(dsrc, login_finish.auth_id)
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

    utc_now = util.utc_timestamp()
    flow_user = FlowUser(
        flow_id=login_finish.flow_id,
        scope=saved_state.scope,
        auth_time=utc_now,
        user_id=saved_state.user_id,
    )

    await data.kv.store_flow_user(dsrc, session_key, flow_user)

    return None


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
    dsrc: Source = request.app.state.dsrc
    try:
        auth_request = AuthRequest(
            response_type=response_type,
            client_id=client_id,
            redirect_uri=redirect_uri,
            state=state,
            code_challenge=code_challenge,
            code_challenge_method=code_challenge_method,
            nonce=nonce,
        )
    except ValidationError as e:
        logger.debug(str(e.errors()))
        raise ErrorResponse(
            status_code=400, err_type="invalid_authorize", err_desc=str(e.errors())
        )

    flow_id = util.random_time_hash_hex()

    await data.kv.store_auth_request(dsrc, flow_id, auth_request)

    # Used to retrieve authentication information
    params = {"flow_id": flow_id}
    redirect = f"{credentials_url}?{urlencode(params)}"

    return RedirectResponse(redirect, status_code=status.HTTP_303_SEE_OTHER)


@router.get("/oauth/callback/", status_code=303)
async def oauth_finish(flow_id: str, code: str, response: Response, request: Request):
    # Prevents cache of value
    response.headers["Cache-Control"] = "no-store"
    response.headers["Pragma"] = "no-cache"

    dsrc: Source = request.app.state.dsrc
    try:
        auth_request = await data.kv.get_auth_request(dsrc, flow_id)
    except NoDataError as e:
        logger.debug(e.message)
        reason = "Expired or missing auth request"
        raise ErrorResponse(400, err_type=f"invalid_oauth_callback", err_desc=reason)

    params = {"code": code, "state": auth_request.state}

    redirect = f"{auth_request.redirect_uri}?{urlencode(params)}"

    return RedirectResponse(redirect, status_code=status.HTTP_303_SEE_OTHER)


@router.post("/oauth/token/", response_model=TokenResponse)
async def token(token_request: TokenRequest, response: Response, request: Request):
    # Prevents cache, required by OpenID Connect
    response.headers["Cache-Control"] = "no-store"
    response.headers["Pragma"] = "no-cache"

    dsrc: Source = request.app.state.dsrc
    # We only allow requests meant to be sent from our front end
    # This does not heighten security, only so other clients do not accidentally make requests here
    if token_request.client_id != frontend_client_id:
        reason = "Invalid client ID."
        logger.debug(reason)
        raise ErrorResponse(400, err_type="invalid_client", err_desc=reason)

    token_type = "Bearer"

    # Two available grant types, 'authorization_code' (after login) and 'refresh_token' (when logged in)
    # The first requires a code provided by the OPAQUE login flow
    if token_request.grant_type == "authorization_code":
        logger.debug(f"authorization_code request")
        # This grant type requires other body parameters than the refresh token grant type
        try:
            assert token_request.redirect_uri
            assert token_request.code_verifier
            assert token_request.code
        except AssertionError:
            reason = "redirect_uri, code and code_verifier must be defined"
            logger.debug(reason)
            raise ErrorResponse(
                400,
                err_type="invalid_request",
                err_desc=reason,
                debug_key="incomplete_code",
            )
        try:
            flow_user = await data.kv.pop_flow_user(dsrc, token_request.code)
        except NoDataError as e:
            logger.debug(e.message)
            reason = "Expired or missing auth code"
            raise ErrorResponse(
                400, err_type="invalid_grant", err_desc=reason, debug_key="empty_flow"
            )

        try:
            auth_request = await data.kv.get_auth_request(dsrc, flow_user.flow_id)
        except NoDataError as e:
            # TODO maybe check auth time just in case
            logger.debug(e.message)
            reason = "Expired or missing auth request"
            raise ErrorResponse(400, err_type=f"invalid_grant", err_desc=reason)

        if token_request.client_id != auth_request.client_id:
            logger.debug(
                f"Request redirect {token_request.client_id} does not match"
                f" {auth_request.client_id}"
            )
            raise ErrorResponse(
                400, err_type="invalid_request", err_desc="Incorrect client_id"
            )
        if token_request.redirect_uri != auth_request.redirect_uri:
            logger.debug(
                f"Request redirect {token_request.redirect_uri} does not match"
                f" {auth_request.redirect_uri}"
            )
            raise ErrorResponse(
                400, err_type="invalid_request", err_desc="Incorrect redirect_uri"
            )

        try:
            # We only support S256, so don't have to check the code_challenge_method
            computed_challenge_hash = hashlib.sha256(
                token_request.code_verifier.encode("ascii")
            ).digest()
            # Remove "=" as we do not store those
            challenge = util.enc_b64url(computed_challenge_hash)
        except UnicodeError:
            reason = "Incorrect code_verifier format"
            logger.debug(f"{reason}: {token_request.code_verifier}")
            raise ErrorResponse(400, err_type=f"invalid_request", err_desc=reason)
        if challenge != auth_request.code_challenge:
            logger.debug(
                f"Computed code challenge {challenge} does not match saved"
                f" {auth_request.code_challenge}"
            )
            raise ErrorResponse(
                400, err_type="invalid_grant", err_desc="Incorrect code_challenge"
            )

        auth_time = flow_user.auth_time
        id_nonce = auth_request.nonce
        token_user_id = flow_user.user_id

        token_scope = flow_user.scope
        id_token, access, refresh, exp, returned_scope = await new_token(
            dsrc, token_user_id, token_scope, auth_time, id_nonce
        )

    elif token_request.grant_type == "refresh_token":
        logger.debug(f"refresh_token request")
        try:
            assert token_request.refresh_token is not None
        except AssertionError as e:
            error_desc = "refresh_token must be defined"
            logger.debug(f"{str(e)}: {error_desc}")
            raise ErrorResponse(
                400, err_type="invalid_grant", err_desc="refresh_token must be defined"
            )

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
        except InvalidRefresh as e:
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
        raise ErrorResponse(400, err_type=f"unsupported_grant_type", err_desc=reason)

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
async def get_users(
    user: str, request: Request, authorization: str = Security(auth_header)
):
    dsrc: Source = request.app.state.dsrc
    acc = await require_user(authorization, dsrc, user)
    return acc.exp


@router.post("/logout/delete/")
async def delete_token(logout: LogoutRequest, request: Request):
    dsrc: Source = request.app.state.dsrc
    await delete_refresh(dsrc, logout.refresh_token)
