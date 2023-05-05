from fastapi import APIRouter, Request

from apiserver.data import Source
from apiserver.lib.model.entities import UserData
from apiserver.app.ops.header import Authorization
from apiserver.app.routers.helper import handle_auth

from apiserver import data

router = APIRouter()


@router.get("/res/profile/", response_model=UserData)
async def get_profile(request: Request, authorization: Authorization):
    dsrc: Source = request.state.dsrc
    acc = await handle_auth(authorization, dsrc)
    async with data.get_conn(dsrc) as conn:
        user_data = await data.user.get_userdata_by_id(conn, acc.sub)

    return user_data