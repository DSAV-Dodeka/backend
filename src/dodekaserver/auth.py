from fastapi import APIRouter
from pydantic import BaseModel

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
        raise ValueError

    session_key = opq.login_finish(login_finish.client_request, saved_state.state)

    return session_key


@router.post("/auth/{username}")
async def save_authorization(username: str, req: AuthRequest):
    # user = await data.get_user_row(dsrc, user_id)
    print(req.state)
    print(req.code_challenge)
    user_usph = util.usp_hex(username)
    print(user_usph)
    auth_id = util.random_user_time_hash_hex(user_usph)
    print(auth_id)
    data.store_json(dsrc.kv, auth_id, req.dict(), 180)

    return {"auth_id": auth_id}
