from typing import Optional

from sqlalchemy.ext.asyncio import AsyncConnection

from apiserver.data.source import DataError, Source
from apiserver.data.use import retrieve_by_id, insert_return_col, delete_by_column, delete_by_id
from apiserver.define.entities import SavedRefreshToken
from apiserver.db.model import REFRESH_TOKEN_TABLE, FAMILY_ID, USER_ID


async def insert_refresh_row(dsrc: Source, conn: AsyncConnection, refresh: SavedRefreshToken) -> int:
    refresh_row = refresh.dict(exclude={'id'})
    return await insert_return_col(dsrc, conn, REFRESH_TOKEN_TABLE, refresh_row, "id")


def parse_refresh(refresh_dict: Optional[dict]) -> SavedRefreshToken:
    if refresh_dict is None:
        raise DataError("Refresh Token does not exist.", "refresh_empty")
    return SavedRefreshToken.parse_obj(refresh_dict)


async def get_refresh_by_id(dsrc: Source, conn: AsyncConnection, id_int: int) -> SavedRefreshToken:
    refresh_row = await retrieve_by_id(dsrc, conn, REFRESH_TOKEN_TABLE, id_int)
    return parse_refresh(refresh_row)


async def delete_family(dsrc: Source, family_id: str):
    return await delete_by_column(dsrc, REFRESH_TOKEN_TABLE, FAMILY_ID, family_id)


async def delete_refresh_by_id(dsrc: Source, conn: AsyncConnection, id_int: int):
    return await delete_by_id(dsrc, conn, REFRESH_TOKEN_TABLE, id_int)


async def delete_by_user_id(dsrc: Source, user_id: str):
    return await delete_by_column(dsrc, REFRESH_TOKEN_TABLE, USER_ID, user_id)
