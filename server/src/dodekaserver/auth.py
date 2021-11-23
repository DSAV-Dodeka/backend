from typing import Union

from fastapi import APIRouter
from pydantic import BaseModel

import dodekaserver.data as data

dsrc = data.dsrc

router = APIRouter()


class AuthRequest(BaseModel):
    response_type: str
    client_id: str
    redirect_uri: str
    state: str
    code_challenge: str
    code_challenge_method: str


@router.post("/auth/{user_id}")
async def save_authorization(user_id: int, req: AuthRequest):
    # user = await data.get_user_row(dsrc, user_id)
    print(req.state)
    print(req.code_challenge)
    data.store_json(dsrc.kv, "user1", req.dict(), 180)


    return ""



