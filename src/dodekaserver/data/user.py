from dodekaserver.data.source import Source
from dodekaserver.db import USER_TABLE
from dodekaserver.db.model import USERNAME, NAME, LAST_NAME, PASSWORD


__all__ = ['get_user_row', 'upsert_user_row', 'create_user', 'get_password']


async def get_user_row(dsrc: Source, id_int: int) -> dict:
    return await dsrc.ops.retrieve_by_id(dsrc.db, USER_TABLE, id_int)


async def get_password(dsrc: Source, usp_hex: str) -> str:
    user_row = await dsrc.ops.retrieve_by_unique(dsrc.db, USER_TABLE, USERNAME, usp_hex)
    return user_row.get(PASSWORD)


async def upsert_user_row(dsrc: Source, user_row: dict):
    return await dsrc.ops.upsert_by_id(dsrc.db, USER_TABLE, user_row)


def create_user(ups_hex, password_file, name, last_name) -> dict:
    return {
        USERNAME: ups_hex,
        NAME: name,
        LAST_NAME: last_name,
        PASSWORD: password_file
    }
