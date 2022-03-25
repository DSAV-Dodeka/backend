from fastapi import APIRouter, Security, status, HTTPException

from dodekaserver.define import ErrorResponse
import dodekaserver.data as data
from dodekaserver.auth.header import handle_header, auth_header, BadAuth

dsrc = data.dsrc

router = APIRouter()


@router.get("/res/profile")
async def get_profile(authorization: str = Security(auth_header)):
    try:
        acc = await handle_header(authorization)
    except BadAuth as e:
        raise ErrorResponse(e.status_code, err_type=e.err_type, err_desc=e.err_desc)

    return {
        "username": acc.sub,
        "scope": acc.scope
    }
