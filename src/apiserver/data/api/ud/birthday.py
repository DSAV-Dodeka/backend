from typing import Optional

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


def parse_birthday_data(birthday_dict: Optional[dict]) -> BirthdayData:
    if birthday_dict is None:
        raise NoDataError("BirthdayData does not exist.", "birthday_data_empty")
    return BirthdayData.model_validate(birthday_dict)


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
    return [parse_birthday_data(dict(bd_dct)) for bd_dct in all_birthdays]
