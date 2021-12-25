import json
from urllib.parse import urlencode
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import RedirectResponse
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel, ValidationError, validator

import opaquepy.lib as opq

import dodekaserver.data as data
import dodekaserver.utilities as util

dsrc = data.dsrc

router = APIRouter()


class AuthRequest(BaseModel):
    response_type: str
    client_id: str
    redirect_uri: str
    state: str
    code_challenge: str
    code_challenge_method: str

    @validator('response_type')
    def check_type(cls, v):
        assert v == "code", "'response_type' must be 'code'"
        return v

    @validator('client_id')
    def check_client(cls, v):
        assert v == "dodekaweb_client", "Unrecognized client ID!"
        return v

    @validator('redirect_uri')
    def check_redirect(cls, v):
        assert v == "http://localhost:3000/callback", "Unrecognized redirect!"
        return v

    @validator('state')
    def check_state(cls, v):
        assert len(v) < 100, "State must not be too long!"
        return v

    # possibly replace for performance
    @validator('code_challenge')
    def check_challenge(cls, v: str):
        assert 128 >= len(v) >= 43, "Length must be 128 >= len >= 43!"
        for c in v:
            assert c.isalnum() or c in "-._~", "Invalid character in challenge!"
        return v


class PasswordRequest(BaseModel):
    username: str
    client_request: str


class PasswordResponse(BaseModel):
    server_message: str
    auth_id: str


class SavedState(BaseModel):
    user_usph: str
    state: str


class FinishRequest(BaseModel):
    auth_id: str
    username: str
    client_request: str


port_front = 3000


@router.get("/oauth/authorize/start")
async def start_oauth(auth_id: str):
    # dedicated page in the future
    return RedirectResponse(f"http://localhost:3000/auth?auth_id={auth_id}")


@router.get("/oauth/authorize/finish")
async def finish_oauth(auth_id: str, code: str):
    auth_req_dict = data.get_json(dsrc.kv, auth_id)
    auth_req = AuthRequest.parse_obj(auth_req_dict)

    url = f"{auth_req.redirect_uri}?state={auth_req.state},code={code}"

    return RedirectResponse(url)


@router.post("/auth/register/start/")
async def start_register(register_start: PasswordRequest):
    public_key = await data.key.get_public_key(dsrc, 0)
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

    new_user = data.user.create_user(user_usph, password_file, "a", "b")

    await data.user.upsert_user_row(dsrc, new_user)


@router.post("/auth/login/start")
async def start_login(login_start: PasswordRequest):
    user_usph = util.usp_hex(login_start.username)
    private_key = await data.key.get_private_key(dsrc, 0)

    password_file = await data.user.get_password(dsrc, user_usph)

    auth_id = util.random_user_time_hash_hex(user_usph)

    response, state = opq.login(password_file, login_start.client_request, private_key)

    saved_state = SavedState(user_usph=user_usph, state=state)
    data.store_json(dsrc.kv, auth_id, saved_state.dict(), 1000)

    return PasswordResponse(server_message=response, auth_id=auth_id)


@router.post("/auth/login/finish")
async def finish_login(login_finish: FinishRequest):
    state_dict = data.get_json(dsrc.kv, login_finish.auth_id)
    saved_state = SavedState.parse_obj(state_dict)

    user_usph = util.usp_hex(login_finish.username)
    if saved_state.user_usph != user_usph:
        raise HTTPException(status_code=400)

    session_key = opq.login_finish(login_finish.client_request, saved_state.state)

    data.store_kv(dsrc.kv, session_key, user_usph, 60)

    return None


@router.get("/oauth/authorize/", status_code=302)
async def oauth_endpoint(response_type: str, client_id: str, redirect_uri: str, state: str,
                         code_challenge: str, code_challenge_method: str):
    try:
        auth_request = AuthRequest(response_type=response_type, client_id=client_id, redirect_uri=redirect_uri,
                                   state=state, code_challenge=code_challenge,
                                   code_challenge_method=code_challenge_method)
    except ValidationError as e:
        raise HTTPException(400, detail=e.errors())
    auth_id = util.random_time_hash_hex()
    data.store_json(dsrc.kv, auth_id, auth_request.dict(), 1000)

    params = {
        "auth_id": auth_id
    }
    redirect = f"http://localhost:3000/auth?{urlencode(params)}"

    return RedirectResponse(redirect)


@router.get("/oauth/callback/")
async def oauth_finish(auth_id: str, code: str):
    auth_req_dict = data.get_json(dsrc.kv, auth_id)
    auth_request = AuthRequest.parse_obj(auth_req_dict)
    return {
        "auth_id": auth_id,
        "code": code,
        "uri": auth_request.redirect_uri
    }


@router.post("/oauth/start/")
async def save_authorization(req: AuthRequest):
    auth_id = util.random_time_hash_hex()
    data.store_json(dsrc.kv, auth_id, req.dict(), 1000)

    return auth_id
