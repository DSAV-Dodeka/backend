from typing import Optional

from dodekaserver.data.source import Source, DataError
from dodekaserver.data.entities import User
from dodekaserver.db import USER_TABLE
from dodekaserver.db.model import USERNAME, NAME, LAST_NAME, PASSWORD


__all__ = ['get_user_by_id', 'upsert_user_row', 'create_user']


def parse_user(user_dict: Optional[dict]) -> User:
    if user_dict is None:
        raise DataError("User does not exist.")
    return User.parse_obj(user_dict)


async def get_user_by_id(dsrc: Source, id_int: int) -> User:
    user_row = await dsrc.ops.retrieve_by_id(dsrc.db, USER_TABLE, id_int)
    return parse_user(user_row)


async def get_user_by_usph(dsrc: Source, usp_hex: str) -> User:
    user_row = await dsrc.ops.retrieve_by_unique(dsrc.db, USER_TABLE, USERNAME, usp_hex)
    return parse_user(user_row)


async def upsert_user_row(dsrc: Source, user_row: dict):
    return await dsrc.ops.upsert_by_id(dsrc.db, USER_TABLE, user_row)


def create_user(ups_hex, password_file, name, last_name) -> dict:
    return {
        USERNAME: ups_hex,
        NAME: name,
        LAST_NAME: last_name,
        PASSWORD: password_file
    }
