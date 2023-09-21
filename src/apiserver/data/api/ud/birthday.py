from typing import List

from pydantic import TypeAdapter
from sqlalchemy import RowMapping
from sqlalchemy.ext.asyncio import AsyncConnection

from apiserver.lib.model.entities import BirthdayData
from schema.model import (
    USERDATA_TABLE,
    UD_FIRSTNAME,
    UD_LASTNAME,
    BIRTHDATE,
    UD_ACTIVE,
    SHOW_AGE,
)
from store.db import select_some_two_where
from store.error import NoDataError

BirthdayList = TypeAdapter(List[BirthdayData])


def parse_birthday_data(birthdays: list[RowMapping]) -> list[BirthdayData]:
    if len(birthdays) == 0:
        raise NoDataError("BirthdayData does not exist.", "birthday_data_empty")
    return BirthdayList.validate_python(birthdays)


async def get_all_birthdays(conn: AsyncConnection) -> list[BirthdayData]:
    all_birthdays = await select_some_two_where(
        conn,
        USERDATA_TABLE,
        {UD_FIRSTNAME, UD_LASTNAME, BIRTHDATE},
        UD_ACTIVE,
        True,
        SHOW_AGE,
        True,
    )
    return parse_birthday_data(all_birthdays)
