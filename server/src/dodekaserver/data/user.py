from databases import Database

from dodekaserver.db import retrieve_by_id, USER_TABLE


async def get_user_row(db: Database, id_int: id):
    return await retrieve_by_id(db, USER_TABLE, id_int)
