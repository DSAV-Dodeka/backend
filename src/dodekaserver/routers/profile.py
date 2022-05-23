from fastapi import APIRouter, Security, status, HTTPException

from dodekaserver.define import ErrorResponse
import dodekaserver.data as data
from dodekaserver.auth.header import handle_header, auth_header, BadAuth
from dodekaserver.define.entities import AccessToken

dsrc = data.dsrc

router = APIRouter()


async def handle_auth(authorization: str) -> AccessToken:
    try:
        return await handle_header(authorization)
    except BadAuth as e:
        raise ErrorResponse(e.status_code, err_type=e.err_type, err_desc=e.err_desc, debug_key=e.debug_key)


@router.get("/res/profile")
async def get_profile(authorization: str = Security(auth_header)):
    acc = await handle_auth(authorization)

    return {
        "username": acc.sub,
        "scope": acc.scope
    }
