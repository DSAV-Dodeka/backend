from typing import Optional

from dodekaserver.data.source import DataError, Source
from dodekaserver.data.use import retrieve_by_id, insert_return_id, delete_insert_return_id_transaction, \
    delete_by_column
from dodekaserver.define.entities import SavedRefreshToken
from dodekaserver.db.model import REFRESH_TOKEN_TABLE, FAMILY_ID


async def refresh_save(dsrc: Source, refresh: SavedRefreshToken) -> int:
    refresh_dict = refresh.dict()
    refresh_dict.pop("id")
    return await insert_refresh_row(dsrc, refresh_dict)


async def insert_refresh_row(dsrc: Source, refresh_row: dict) -> int:
    return await insert_return_id(dsrc, REFRESH_TOKEN_TABLE, refresh_row)


def parse_refresh(refresh_dict: Optional[dict]) -> SavedRefreshToken:
    if refresh_dict is None:
        raise DataError("Refresh Token does not exist.", "refresh_empty")
    return SavedRefreshToken.parse_obj(refresh_dict)


async def get_refresh_by_id(dsrc: Source, id_int: int) -> SavedRefreshToken:
    refresh_row = await retrieve_by_id(dsrc, REFRESH_TOKEN_TABLE, id_int)
    return parse_refresh(refresh_row)


async def refresh_transaction(dsrc: Source, id_int_delete: int, new_refresh: SavedRefreshToken) -> int:
    # CURRENTLY DOES NOT FAIL IF IT DOES NOT EXIST
    # TODO add check in query delete if it did delete
    refresh_dict = new_refresh.dict()
    refresh_dict.pop("id")
    return await delete_insert_return_id_transaction(dsrc, REFRESH_TOKEN_TABLE, id_int_delete, refresh_dict)


async def delete_family(dsrc: Source, family_id: str):
    return await delete_by_column(dsrc, REFRESH_TOKEN_TABLE, FAMILY_ID, family_id)
