from dodekaserver.data.source import Source
from dodekaserver.data.entities import SavedRefreshToken
from dodekaserver.db.model import FAMILY_ID, ACCESS_VALUE, REFRESH_TOKEN_TABLE


async def refresh_save(dsrc: Source, refresh: SavedRefreshToken):
    refresh_dict = refresh.dict()
    refresh_dict.pop("id")
    return await insert_refresh_row(dsrc, refresh_dict)


async def insert_refresh_row(dsrc: Source, refresh_row: dict):
    return await dsrc.ops.insert_return_id(dsrc.db, REFRESH_TOKEN_TABLE, refresh_row)

