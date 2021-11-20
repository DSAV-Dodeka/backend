from dodekaserver.data.source import Source
from dodekaserver.db import retrieve_by_id, upsert_by_id, USER_TABLE


__all__ = ['get_user_row', 'upsert_user_row']


async def get_user_row(dsrc: Source, id_int: id):
    print("hi1")
    return await retrieve_by_id(dsrc.db, USER_TABLE, id_int)


async def upsert_user_row(dsrc: Source, user_row: dict):
    return await upsert_by_id(dsrc.db, USER_TABLE, user_row)
