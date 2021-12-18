from typing import Union

from fastapi import APIRouter
from pydantic import BaseModel

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
