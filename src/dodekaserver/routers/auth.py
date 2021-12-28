from typing import Optional
from urllib.parse import urlencode
from fastapi import APIRouter, HTTPException, status
from fastapi.responses import RedirectResponse
from pydantic import ValidationError
import opaquepy.lib as opq

import dodekaserver.data as data
from dodekaserver.data import DataError
import dodekaserver.utilities as util
from dodekaserver.auth.models import *
from dodekaserver.auth.tokens import *

dsrc = data.dsrc

router = APIRouter()


port_front = 3000


@router.post("/auth/register/start/")
async def start_register(register_start: PasswordRequest):
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


@router.post("/auth/login/start")
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
    flow_user = FlowUser(flow_id=login_finish.flow_id, user_usph=user_usph)

    data.store_json(dsrc.kv, session_key, flow_user.dict(), 60)

    return None


@router.get("/oauth/authorize/")
async def oauth_endpoint(response_type: str, client_id: str, redirect_uri: str, state: str,
                         code_challenge: str, code_challenge_method: str):
    try:
        auth_request = AuthRequest(response_type=response_type, client_id=client_id, redirect_uri=redirect_uri,
                                   state=state, code_challenge=code_challenge,
                                   code_challenge_method=code_challenge_method)
    except ValidationError as e:
        raise HTTPException(400, detail=e.errors())
    flow_id = util.random_time_hash_hex()
    data.store_json(dsrc.kv, flow_id, auth_request.dict(), 1000)

    params = {
        "flow_id": flow_id
    }
    redirect = f"http://localhost:3000/auth/credentials?{urlencode(params)}"

    return RedirectResponse(redirect, status_code=status.HTTP_302_FOUND)


@router.get("/oauth/callback/", status_code=302)
async def oauth_finish(flow_id: str, code: str):
    auth_req_dict = data.get_json(dsrc.kv, flow_id)
    auth_request = AuthRequest.parse_obj(auth_req_dict)
    params = {
        "code": code,
        "state": auth_request.state
    }
    redirect = f"{auth_request.redirect_uri}?{urlencode(params)}"
    print("xxx")
    return RedirectResponse(redirect, status_code=status.HTTP_302_FOUND)


@router.post("/oauth/token/")
async def token(token_request: TokenRequest):
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
        auth_request = AuthRequest.parse_obj(auth_req_dict)

        jwt = await create_refresh_access_pair(dsrc, flow_user.user_usph, "test")

        return jwt
    elif token_request.grant_type == "refresh_token":
        try:
            assert token_request.refresh_token is not None
        except AssertionError:
            raise HTTPException(400, detail="refresh_token must be defined")

        jwt = await create_refresh_access_pair(dsrc, refresh_token=token_request.refresh_token)
    else:
        return None
