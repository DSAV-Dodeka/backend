from typing import List

from fastapi import APIRouter, Request
from pydantic import TypeAdapter

import apiserver.data.api.ud.birthday
from apiserver import data
from apiserver.app.error import ErrorResponse
from apiserver.app.ops.header import Authorization
from apiserver.app.response import RawJSONResponse
from apiserver.app.routers.helper import require_member
from apiserver.data import Source
from apiserver.lib.model.entities import BirthdayData, UserPointsNamesList

router = APIRouter()

BirthdayList = TypeAdapter(List[BirthdayData])


@router.get("/members/birthdays/", response_model=list[BirthdayData])
async def get_user_birthdays(request: Request, authorization: Authorization):
    dsrc: Source = request.state.dsrc
    await require_member(authorization, dsrc)

    async with data.get_conn(dsrc) as conn:
        birthday_data = await apiserver.data.api.ud.birthday.get_all_birthdays(conn)

    return RawJSONResponse(BirthdayList.dump_json(birthday_data))
