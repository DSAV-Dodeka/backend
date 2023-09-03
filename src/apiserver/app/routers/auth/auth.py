import logging

from fastapi import APIRouter, Response, Request
from fastapi.responses import RedirectResponse
from pydantic import BaseModel

import auth.core.util
import auth.data.authentication
from apiserver import data
from apiserver.app.error import ErrorResponse
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
from apiserver.define import LOGGER_NAME, DEFINE
from auth.core.error import RedirectError, AuthError
from auth.core.model import PasswordRequest, FinishLogin
from auth.core.response import PasswordResponse
from auth.modules.authorize import oauth_start, oauth_callback
from auth.modules.login import (
    start_login as auth_start_login,
    finish_login as auth_finish_login,
)

router = APIRouter()

port_front = 3000

logger = logging.getLogger(LOGGER_NAME)


@router.post("/login/start/", response_model=PasswordResponse)
async def start_login(login_start: PasswordRequest, request: Request):
    """Login can be initiated in 2 different flows: the first is the OAuth 2 flow, the second is a simple password
    check flow."""
    dsrc: Source = request.state.dsrc

    return await auth_start_login(dsrc.store, data.user.UserOps, login_start)


@router.post("/login/finish/")
async def finish_login(login_finish: FinishLogin, request: Request):
    dsrc: Source = request.state.dsrc

    try:
        await auth_finish_login(dsrc.store, login_finish)
    except AuthError as e:
        raise ErrorResponse(
            status_code=400,
            err_type=e.err_type,
            err_desc=e.err_desc,
        )


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
            DEFINE,
            dsrc.store,
            response_type,
            client_id,
            redirect_uri,
            state,
            code_challenge,
            code_challenge_method,
            nonce,
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
        redirect = await oauth_callback(dsrc.store, flow_id, code)
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
            flow_user = await auth.data.authentication.pop_flow_user(
                dsrc.store, token_request.code
            )
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
