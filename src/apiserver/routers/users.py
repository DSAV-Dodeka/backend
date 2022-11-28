from apiserver.define.entities import BirthdayData
from fastapi import APIRouter, Security, Request
import apiserver.data as data
from apiserver.data import Source
from apiserver.auth.header import auth_header
from apiserver.routers.helper import require_member

router = APIRouter()


@router.get("/members/birthdays/", response_model=list[BirthdayData])
async def get_users(request: Request, authorization: str = Security(auth_header)):
    dsrc: Source = request.app.state.dsrc
    await require_member(authorization, dsrc)

    async with data.get_conn(dsrc) as conn:
        birthday_data = await data.user.get_all_birthdays(dsrc, conn)
    return birthday_data
