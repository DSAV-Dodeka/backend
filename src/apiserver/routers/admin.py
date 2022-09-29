import logging

from fastapi import APIRouter, Security, Request

from apiserver.define import LOGGER_NAME
from apiserver.define.entities import UserData
import apiserver.data as data
from apiserver.data import Source
from apiserver.auth.header import auth_header
from apiserver.routers.helper import require_admin

router = APIRouter()

logger = logging.getLogger(LOGGER_NAME)


@router.get("/admin/users/", response_model=list[UserData])
async def get_users(request: Request, authorization: str = Security(auth_header)):
    dsrc: Source = request.app.state.dsrc
    await require_admin(authorization, dsrc)
    async with data.get_conn(dsrc) as conn:
        user_data = await data.user.get_all_userdata(dsrc, conn)
    return user_data
