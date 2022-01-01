from typing import Optional

from dodekaserver.data.source import Source, DataError
from dodekaserver.data.entities import SavedRefreshToken
from dodekaserver.db.model import REFRESH_TOKEN_TABLE


async def refresh_save(dsrc: Source, refresh: SavedRefreshToken) -> int:
    refresh_dict = refresh.dict()
    refresh_dict.pop("id")
    return await insert_refresh_row(dsrc, refresh_dict)


async def insert_refresh_row(dsrc: Source, refresh_row: dict) -> int:
    return await dsrc.ops.insert_return_id(dsrc.db, REFRESH_TOKEN_TABLE, refresh_row)


def parse_refresh(user_dict: Optional[dict]) -> SavedRefreshToken:
    if user_dict is None:
        raise DataError("Refresh Token does not exist.")
    return SavedRefreshToken.parse_obj(user_dict)


async def get_refresh_by_id(dsrc: Source, id_int: int) -> SavedRefreshToken:
    refresh_row = await dsrc.ops.retrieve_by_id(dsrc.db, REFRESH_TOKEN_TABLE, id_int)
    return parse_refresh(refresh_row)


async def refresh_transaction(dsrc: Source, id_int_delete: int, new_refresh: SavedRefreshToken) -> int:
    refresh_dict = new_refresh.dict()
    refresh_dict.pop("id")
    return await dsrc.ops.delete_insert_return_id_transaction(dsrc.db, REFRESH_TOKEN_TABLE, id_int_delete, refresh_dict)
