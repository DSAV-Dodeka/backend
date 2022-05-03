from typing import Optional

from dodekaserver.data.source import DataError, Gateway
from dodekaserver.define.entities import SavedRefreshToken
from dodekaserver.db.model import REFRESH_TOKEN_TABLE, FAMILY_ID
from dodekaserver.db.use import retrieve_by_id


async def refresh_save(gtw: Gateway, refresh: SavedRefreshToken) -> int:
    refresh_dict = refresh.dict()
    refresh_dict.pop("id")
    return await insert_refresh_row(gtw, refresh_dict)


async def insert_refresh_row(gtw: Gateway, refresh_row: dict) -> int:
    return await gtw.ops.insert_return_id(gtw.db, REFRESH_TOKEN_TABLE, refresh_row)


def parse_refresh(refresh_dict: Optional[dict]) -> SavedRefreshToken:
    if refresh_dict is None:
        raise DataError("Refresh Token does not exist.", "refresh_empty")
    return SavedRefreshToken.parse_obj(refresh_dict)


async def query_refresh_by_id(gtw: Gateway, id_int: int) -> SavedRefreshToken:
    refresh_row = await retrieve_by_id(gtw.db, REFRESH_TOKEN_TABLE, id_int)
    return parse_refresh(refresh_row)


async def query_refresh_transaction(gtw: Gateway, id_int_delete: int, new_refresh: SavedRefreshToken) -> int:
    # CURRENTLY DOES NOT FAIL IF IT DOES NOT EXIST
    # TODO add check in query delete if it did delete
    refresh_dict = new_refresh.dict()
    refresh_dict.pop("id")
    return await gtw.ops.delete_insert_return_id_transaction(gtw.db, REFRESH_TOKEN_TABLE, id_int_delete, refresh_dict)


async def query_delete_family(gtw: Gateway, family_id: str):
    return await gtw.ops.delete_by_column(gtw.db, REFRESH_TOKEN_TABLE, FAMILY_ID, family_id)
