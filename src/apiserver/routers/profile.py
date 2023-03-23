from fastapi import APIRouter, Request

from apiserver.data import Source
from apiserver.define.entities import UserData
from apiserver.auth.header import Authorization
from apiserver.routers.helper import handle_auth

from apiserver import data

router = APIRouter()


@router.get("/res/profile/", response_model=UserData)
async def get_profile(request: Request, authorization: Authorization):
    dsrc: Source = request.state.dsrc
    acc = await handle_auth(authorization, dsrc)
    async with data.get_conn(dsrc) as conn:
        user_data = await data.user.get_userdata_by_id(dsrc, conn, acc.sub)

    return user_data
