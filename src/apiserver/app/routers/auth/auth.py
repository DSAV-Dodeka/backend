import logging

from fastapi import APIRouter, Response, Request
from fastapi.responses import RedirectResponse
from pydantic import BaseModel

from apiserver import data
from apiserver.app.error import ErrorResponse
from apiserver.app.ops.header import Authorization
from auth.modules.token.create import delete_refresh
from apiserver.app.routers.auth.validations import (
    TokenRequest,
    TokenResponse,
)
from apiserver.app.routers.helper import require_user
from apiserver.data import Source
from auth.modules.token.process import process_token_request
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

    try:
        token_response = await process_token_request(
            dsrc.store, DEFINE, data.schema.SCHEMA, dsrc.key_state, token_request
        )
    except AuthError as e:
        raise ErrorResponse(400, err_type=e.err_type, err_desc=e.err_desc)

    return token_response


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
