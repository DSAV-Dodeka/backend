from databases import Database

from dodekaserver.db import retrieve_by_id, upsert_by_id, USER_TABLE


async def get_user_row(db: Database, id_int: id):
    return await retrieve_by_id(db, USER_TABLE, id_int)


async def upsert_user_row(db: Database, user_row: dict):
    return await upsert_by_id(db, USER_TABLE, user_row)