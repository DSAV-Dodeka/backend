from typing import List

from fastapi import APIRouter, Depends
from pydantic import TypeAdapter
from apiserver.app.dependencies import SourceDep, require_member

import apiserver.data.api.ud.birthday
from apiserver import data
from apiserver.app.response import RawJSONResponse
from apiserver.lib.model.entities import BirthdayData

members_router = APIRouter(
    prefix="/members", tags=["members"], dependencies=[Depends(require_member)]
)

BirthdayList = TypeAdapter(List[BirthdayData])


@members_router.get("/members/birthdays/", response_model=list[BirthdayData])
async def get_user_birthdays(dsrc: SourceDep) -> RawJSONResponse:
    async with data.get_conn(dsrc) as conn:
        birthday_data = await apiserver.data.api.ud.birthday.get_all_birthdays(conn)

    return RawJSONResponse(BirthdayList.dump_json(birthday_data))
