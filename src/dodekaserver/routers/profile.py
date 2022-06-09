from fastapi import APIRouter, Security

import dodekaserver.data as data
from dodekaserver.auth.header import auth_header
from dodekaserver.routers.helper import handle_auth

dsrc = data.dsrc

router = APIRouter()


@router.get("/res/profile")
async def get_profile(authorization: str = Security(auth_header)):
    acc = await handle_auth(authorization)

    return {
        "username": acc.sub,
        "scope": acc.scope
    }
