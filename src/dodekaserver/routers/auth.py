import hashlib
from urllib.parse import urlencode
import logging

from pydantic import ValidationError
from fastapi import APIRouter, HTTPException, status, Response, BackgroundTasks
from fastapi.responses import RedirectResponse

import opaquepy as opq

from dodekaserver.define.entities import User
from dodekaserver.env import LOGGER_NAME, frontend_client_id, credentials_url
from dodekaserver.define import ErrorResponse, PasswordResponse, PasswordRequest, SavedState, FinishRequest, \
    FinishLogin, AuthRequest, TokenResponse, TokenRequest, FlowUser, RegisterRequest
import dodekaserver.utilities as util
import dodekaserver.data as data
from dodekaserver.data import DataError, NoDataError
import dodekaserver.auth.authentication as authentication
from dodekaserver.auth.tokens import InvalidRefresh
from dodekaserver.auth.tokens_data import do_refresh, new_token

dsrc = data.dsrc

router = APIRouter()

port_front = 3000

logger = logging.getLogger(LOGGER_NAME)


@router.post("/register/start/", response_model=PasswordResponse)
async def start_register(register_start: RegisterRequest):
    """ First step of OPAQUE registration, requires username and client message generated in first client registration
    step."""
    email_usph = util.usp_hex(register_start.email)
    try:
        ud = await data.user.get_userdata_by_register_id(dsrc, register_start.registerid)
    except DataError as e:
        logger.debug(e)
        reason = "No registration for that register_id"
        raise ErrorResponse(400, err_type="invalid_register", err_desc=reason, debug_key="no_register_for_id")

    try:
        u = await data.user.get_user_by_id(dsrc, ud.id)
    except DataError as e:
        logger.debug(e)
        reason = "No registration for that user"
        raise ErrorResponse(400, err_type="invalid_register", err_desc=reason, debug_key="no_register_for_user")

    if ud.registered or len(u.password_file) > 0:
        logger.debug("Already registered.")
        reason = "Bad registration."
        raise ErrorResponse(400, err_type="invalid_register", err_desc=reason, debug_key="bad_registration_start")

    if ud.email != email_usph:
        logger.debug("Registration start does not match e-mail")
        reason = "Bad registration."
        raise ErrorResponse(400, err_type="invalid_register", err_desc=reason, debug_key="bad_registration_start")

    # OPAQUE public key
    public_key = await data.key.get_opaque_public(dsrc)
    auth_id = util.random_time_hash_hex(email_usph)

    response, saved_state = authentication.opaque_register(register_start.client_request, public_key, email_usph, ud.id)

    await data.kv.store_auth_register_state(dsrc, auth_id, saved_state)

    return PasswordResponse(server_message=response, auth_id=auth_id)


@router.post("/register/finish/")
async def finish_register(register_finish: FinishRequest):
    try:
        saved_state = await data.kv.get_register_state(dsrc, register_finish.auth_id)
    except NoDataError as e:
        logger.debug(e.message)
        reason = "Registration not initialized or expired"
        raise ErrorResponse(400, err_type="invalid_registration", err_desc=reason, debug_key="no_register_start")

    email_usph = util.usp_hex(register_finish.email)
    if saved_state.user_usph != email_usph:
        reason = "User does not match state!"
        logger.debug(reason)
        raise ErrorResponse(400, err_type="invalid_registration", err_desc=reason, debug_key="unequal_user")

    password_file = opq.register_finish(register_finish.client_request, saved_state.state)

    new_user = User(id=saved_state.id, usp_hex=email_usph, password_file=password_file).dict()

    try:
        await data.user.upsert_user_row(dsrc, new_user)
    except DataError as e:
        logger.debug(e.message)
        if e.key == "unique_violation":
            raise ErrorResponse(400, err_type="invalid_registration", err_desc="Username already exists!",
                                debug_key="user_exists")
        else:
            raise e


@router.post("/login/start/", response_model=PasswordResponse)
async def start_login(login_start: PasswordRequest):
    user_usph = util.usp_hex(login_start.email)
    private_key = await data.key.get_opaque_private(dsrc)

    password_file = await data.user.get_user_password_file(dsrc, "fakerecord")
    data_password = ""
    try:
        data_password = await data.user.get_user_password_file(dsrc, user_usph)

    except NoDataError:
        # If user does not exist, pass fake user record to prevent client enumeration
        # TODO ensure this fake record exists
        pass
    # If password is empty or was not set due to non-existent user, make login impossible
    if data_password:
        password_file = data_password

    auth_id = util.random_time_hash_hex(user_usph)

    response, state = opq.login(password_file, login_start.client_request, private_key)

    saved_state = SavedState(user_usph=user_usph, state=state)

    await data.kv.store_auth_state(dsrc, auth_id, saved_state)

    return PasswordResponse(server_message=response, auth_id=auth_id)


@router.post("/login/finish/")
async def finish_login(login_finish: FinishLogin):
    try:
        saved_state = await data.kv.get_state(dsrc, login_finish.auth_id)
    except NoDataError as e:
        logger.debug(e.message)
        reason = "Login not initialized or expired"
        raise ErrorResponse(400, err_type="invalid_login", err_desc=reason, debug_key="no_login_start")

    user_usph = util.usp_hex(login_finish.email)
    if saved_state.user_usph != user_usph:
        raise ErrorResponse(status_code=400, err_type="invalid_login", err_desc="Incorrect username for this login!")

    session_key = opq.login_finish(login_finish.client_request, saved_state.state)
    utc_now = util.utc_timestamp()
    flow_user = FlowUser(flow_id=login_finish.flow_id, user_usph=user_usph, auth_time=utc_now)

    await data.kv.store_flow_user(dsrc, session_key, flow_user)

    return None


@router.get("/oauth/authorize/", status_code=303)
async def oauth_endpoint(response_type: str, client_id: str, redirect_uri: str, state: str,
                         code_challenge: str, code_challenge_method: str, nonce: str):
    try:
        auth_request = AuthRequest(response_type=response_type, client_id=client_id, redirect_uri=redirect_uri,
                                   state=state, code_challenge=code_challenge,
                                   code_challenge_method=code_challenge_method, nonce=nonce)
    except ValidationError as e:
        logger.debug(str(e.errors()))
        raise ErrorResponse(status_code=400, err_type="invalid_authorize", err_desc=str(e.errors()))

    flow_id = util.random_time_hash_hex()

    await data.kv.store_auth_request(dsrc, flow_id, auth_request)

    # Used to retrieve authentication information
    params = {
        "flow_id": flow_id
    }

    redirect = f"{credentials_url}?{urlencode(params)}"

    return RedirectResponse(redirect, status_code=status.HTTP_303_SEE_OTHER)


@router.get("/oauth/callback/", status_code=303)
async def oauth_finish(flow_id: str, code: str, response: Response):
    # Prevents cache of value
    response.headers["Cache-Control"] = "no-store"
    response.headers["Pragma"] = "no-cache"

    try:
        auth_request = await data.kv.get_auth_request(dsrc, flow_id)
    except NoDataError as e:
        logger.debug(e.message)
        reason = "Expired or missing auth request"
        raise ErrorResponse(400, err_type=f"invalid_oauth_callback", err_desc=reason)

    params = {
        "code": code,
        "state": auth_request.state
    }

    redirect = f"{auth_request.redirect_uri}?{urlencode(params)}"

    return RedirectResponse(redirect, status_code=status.HTTP_303_SEE_OTHER)


@router.post("/oauth/token/", response_model=TokenResponse)
async def token(token_request: TokenRequest, response: Response):
    # Prevents cache, required by OpenID Connect
    response.headers["Cache-Control"] = "no-store"
    response.headers["Pragma"] = "no-cache"

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
        # This grant type requires other body parameters than the refresh token grant type

        try:
            assert token_request.redirect_uri
            assert token_request.code_verifier
            assert token_request.code
        except AssertionError:
            reason = "redirect_uri, code and code_verifier must be defined"
            logger.debug(reason)
            raise ErrorResponse(400, err_type="invalid_request", err_desc=reason, debug_key="incomplete_code")
        try:
            flow_user = await data.kv.get_flow_user(dsrc, token_request.code)
        except NoDataError as e:
            logger.debug(e.message)
            reason = "Expired or missing auth code"
            raise ErrorResponse(400, err_type="invalid_grant", err_desc=reason, debug_key="empty_flow")

        try:
            auth_request = await data.kv.get_auth_request(dsrc, flow_user.flow_id)
        except NoDataError as e:
            # TODO maybe check auth time just in case
            logger.debug(e.message)
            reason = "Expired or missing auth request"
            raise ErrorResponse(400, err_type=f"invalid_grant", err_desc=reason)
        # TODO get scope from request

        if token_request.client_id != auth_request.client_id:
            logger.debug(f'Request redirect {token_request.client_id} does not match {auth_request.client_id}')
            raise ErrorResponse(400, err_type="invalid_request", err_desc="Incorrect client_id")
        if token_request.redirect_uri != auth_request.redirect_uri:
            logger.debug(f'Request redirect {token_request.redirect_uri} does not match {auth_request.redirect_uri}')
            raise ErrorResponse(400, err_type="invalid_request", err_desc="Incorrect redirect_uri")

        try:
            # We only support S256, so don't have to check the code_challenge_method
            computed_challenge_hash = hashlib.sha256(token_request.code_verifier.encode('ascii')).digest()
            # Remove "=" as we do not store those
            challenge = util.enc_b64url(computed_challenge_hash)
        except UnicodeError:
            reason = "Incorrect code_verifier format"
            logger.debug(f'{reason}: {token_request.code_verifier}')
            raise ErrorResponse(400, err_type=f"invalid_request", err_desc=reason)
        if challenge != auth_request.code_challenge:
            logger.debug(f'Computed code challenge {challenge} does not match saved {auth_request.code_challenge}')
            raise ErrorResponse(400, err_type="invalid_grant", err_desc="Incorrect code_challenge")

        auth_time = flow_user.auth_time
        id_nonce = auth_request.nonce
        token_user = flow_user.user_usph

        token_scope = "test" if token_user != "admin" else "admin"
        id_token, access, refresh, exp, returned_scope = \
            await new_token(dsrc, token_user, token_scope, auth_time, id_nonce)

    elif token_request.grant_type == "refresh_token":
        try:
            assert token_request.refresh_token is not None
        except AssertionError as e:
            logger.debug(e)
            raise ErrorResponse(400, err_type="invalid_grant", err_desc="refresh_token must be defined")

        old_refresh = token_request.refresh_token

        try:
            id_token, access, refresh, exp, returned_scope, token_user = await do_refresh(dsrc, old_refresh)
        except InvalidRefresh as e:
            logger.debug(e)
            raise ErrorResponse(400, err_type="invalid_grant", err_desc="Invalid refresh_token!")

    else:
        reason = "Only 'refresh_token' and 'authorization_code' grant types are available."
        logger.debug(f'{reason} Used: {token_request.grant_type}')
        raise ErrorResponse(400, err_type=f"unsupported_grant_type", err_desc=reason)

    # TODO login options
    logger.info(f"Token request granted for {token_user}")
    return TokenResponse(id_token=id_token, access_token=access, refresh_token=refresh, token_type=token_type,
                         expires_in=exp, scope=returned_scope)
