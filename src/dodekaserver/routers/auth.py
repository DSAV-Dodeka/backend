import base64
import hashlib
from urllib.parse import urlencode

from pydantic import ValidationError
from fastapi import APIRouter, HTTPException, status, Response
from fastapi.responses import RedirectResponse

import opaquepy.lib as opq

import dodekaserver.data as data
from dodekaserver.data import DataError
import dodekaserver.utilities as util
from dodekaserver.auth.models import *
from dodekaserver.auth.tokens import *

dsrc = data.dsrc

router = APIRouter()

port_front = 3000


@router.post("/auth/register/start/", response_model=PasswordResponse)
async def start_register(register_start: PasswordRequest):
    """ First step of OPAQUE registration, requires username and client message generated in first client registration
    step."""
    # OPAQUE public key
    public_key = await data.key.get_opaque_public(dsrc)
    username = register_start.username
    user_usph = util.usp_hex(username)
    auth_id = util.random_user_time_hash_hex(user_usph)

    response, state = opq.register(register_start.client_request, public_key)
    saved_state = SavedState(user_usph=user_usph, state=state)
    data.store_json(dsrc.kv, auth_id, saved_state.dict(), 1000)

    return PasswordResponse(server_message=response, auth_id=auth_id)


@router.post("/auth/register/finish")
async def finish_register(register_finish: FinishRequest):
    state_dict = data.get_json(dsrc.kv, register_finish.auth_id)
    saved_state = SavedState.parse_obj(state_dict)

    user_usph = util.usp_hex(register_finish.username)
    if saved_state.user_usph != user_usph:
        raise ValueError

    password_file = opq.register_finish(register_finish.client_request, saved_state.state)

    new_user = data.user.create_user(user_usph, password_file)

    await data.user.upsert_user_row(dsrc, new_user)


@router.post("/auth/login/start", response_model=PasswordResponse)
async def start_login(login_start: PasswordRequest):
    user_usph = util.usp_hex(login_start.username)
    private_key = await data.key.get_opaque_private(dsrc)

    try:
        password_file = (await data.user.get_user_by_usph(dsrc, user_usph)).password_file
    except DataError:
        # If user does not exist, pass fake user record to prevent client enumeration
        # TODO ensure this fake record exists
        password_file = (await data.user.get_user_by_id(dsrc, 0)).password_file

    auth_id = util.random_user_time_hash_hex(user_usph)

    response, state = opq.login(password_file, login_start.client_request, private_key)

    saved_state = SavedState(user_usph=user_usph, state=state)
    data.store_json(dsrc.kv, auth_id, saved_state.dict(), 1000)

    return PasswordResponse(server_message=response, auth_id=auth_id)


@router.post("/auth/login/finish")
async def finish_login(login_finish: FinishLogin):
    state_dict = data.get_json(dsrc.kv, login_finish.auth_id)
    saved_state = SavedState.parse_obj(state_dict)

    user_usph = util.usp_hex(login_finish.username)
    if saved_state.user_usph != user_usph:
        raise HTTPException(status_code=400, detail="Incorrect username for this login!")

    session_key = opq.login_finish(login_finish.client_request, saved_state.state)
    utc_now = util.utc_timestamp()
    flow_user = FlowUser(flow_id=login_finish.flow_id, user_usph=user_usph, auth_time=utc_now)

    data.store_json(dsrc.kv, session_key, flow_user.dict(), 60)

    return None


@router.get("/oauth/authorize/")
async def oauth_endpoint(response_type: str, client_id: str, redirect_uri: str, state: str,
                         code_challenge: str, code_challenge_method: str, nonce: str):
    try:
        auth_request = AuthRequest(response_type=response_type, client_id=client_id, redirect_uri=redirect_uri,
                                   state=state, code_challenge=code_challenge,
                                   code_challenge_method=code_challenge_method, nonce=nonce)
    except ValidationError as e:
        raise HTTPException(400, detail=e.errors())
    flow_id = util.random_time_hash_hex()
    data.store_json(dsrc.kv, flow_id, auth_request.dict(), expire=1000)

    # Used to retrieve authentication information
    params = {
        "flow_id": flow_id
    }
    # In the future, we would redirect to some external auth page
    redirect = f"http://localhost:{port_front}/auth/credentials?{urlencode(params)}"

    return RedirectResponse(redirect, status_code=status.HTTP_302_FOUND)


@router.get("/oauth/callback/", status_code=302)
async def oauth_finish(flow_id: str, code: str, response: Response):
    # Prevents cache of value
    response.headers["Cache-Control"] = "no-store"
    response.headers["Pragma"] = "no-cache"

    auth_req_dict = data.get_json(dsrc.kv, flow_id)
    auth_request = AuthRequest.parse_obj(auth_req_dict)
    params = {
        "code": code,
        "state": auth_request.state
    }
    redirect = f"{auth_request.redirect_uri}?{urlencode(params)}"
    return RedirectResponse(redirect, status_code=status.HTTP_302_FOUND)


@router.post("/oauth/token/", response_model=TokenResponse)
async def token(token_request: TokenRequest, response: Response):
    # Prevents cache, required by OpenID Connect
    response.headers["Cache-Control"] = "no-store"
    response.headers["Pragma"] = "no-cache"

    if token_request.client_id != "dodekaweb_client":
        raise HTTPException(400, detail="Invalid client ID.")

    if token_request.grant_type == "authorization_code":
        try:
            assert token_request.redirect_uri is not None
            assert token_request.code_verifier is not None
            assert token_request.code is not None
        except AssertionError:
            raise HTTPException(400, detail="redirect_uri, code and code_verifier must be defined")

        flow_user_dict = data.get_json(dsrc.kv, token_request.code)
        if flow_user_dict is None:
            raise HTTPException(400)
        flow_user = FlowUser.parse_obj(flow_user_dict)
        auth_req_dict = data.get_json(dsrc.kv, flow_user.flow_id)
        if auth_req_dict is None:
            raise HTTPException(400)
        # TODO get scope from request
        auth_request = AuthRequest.parse_obj(auth_req_dict)

        if token_request.client_id != auth_request.client_id:
            raise HTTPException(400, detail="Incorrect client_id")
        if token_request.redirect_uri != auth_request.redirect_uri:
            raise HTTPException(400, detail="Incorrect redirect_uri")

        try:
            # We only support S256, so don't have to check the code_challenge_method
            computed_challenge_hash = hashlib.sha256(token_request.code_verifier.encode('ascii')).digest()
            challenge = base64.urlsafe_b64encode(computed_challenge_hash).decode('utf-8')
        except UnicodeError:
            raise HTTPException(400, detail="Incorrect code_verifier format")
        if challenge != auth_request.code_challenge:
            raise HTTPException(400, detail="Incorrect code_challenge")

        auth_time = flow_user.auth_time
        id_nonce = auth_request.nonce
        token_user = flow_user.user_usph
        token_scope = "test"
        old_refresh = None

    elif token_request.grant_type == "refresh_token":
        try:
            assert token_request.refresh_token is not None
        except AssertionError:
            raise HTTPException(400, detail="refresh_token must be defined")

        auth_time = None
        id_nonce = None
        token_user = None
        token_scope = None
        old_refresh = token_request.refresh_token

    else:
        raise HTTPException(400, detail="Only 'refresh_token' and 'authorization_code' grant types are available.")

    try:
        id_token, access, refresh, token_type, exp, returned_scope = \
            await create_id_access_refresh(dsrc, token_user, token_scope, id_nonce, auth_time,
                                           refresh_token=old_refresh)
    except InvalidRefresh:
        raise HTTPException(400, detail="Invalid refresh_token!")
    # TODO login options
    return TokenResponse(id_token=id_token, access_token=access, refresh_token=refresh, token_type=token_type,
                         expires_in=exp, scope=returned_scope)
