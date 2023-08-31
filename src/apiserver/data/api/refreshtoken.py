from typing import Optional

from sqlalchemy.ext.asyncio import AsyncConnection

from store.db import (
    retrieve_by_id,
    insert_return_col,
    delete_by_column,
    delete_by_id,
)
from apiserver.data.schema.model import REFRESH_TOKEN_TABLE, FAMILY_ID, USER_ID
from apiserver.data.source import DataError
from apiserver.lib.model.entities import SavedRefreshToken


async def insert_refresh_row(conn: AsyncConnection, refresh: SavedRefreshToken) -> int:
    refresh_row = refresh.model_dump(exclude={"id"})
    return await insert_return_col(conn, REFRESH_TOKEN_TABLE, refresh_row, "id")


def parse_refresh(refresh_dict: Optional[dict]) -> SavedRefreshToken:
    if refresh_dict is None:
        raise DataError("Refresh Token does not exist.", "refresh_empty")
    return SavedRefreshToken.model_validate(refresh_dict)


async def get_refresh_by_id(conn: AsyncConnection, id_int: int) -> SavedRefreshToken:
    refresh_row = await retrieve_by_id(conn, REFRESH_TOKEN_TABLE, id_int)
    return parse_refresh(refresh_row)


async def delete_family(conn: AsyncConnection, family_id: str):
    return await delete_by_column(conn, REFRESH_TOKEN_TABLE, FAMILY_ID, family_id)


async def delete_refresh_by_id(conn: AsyncConnection, id_int: int):
    return await delete_by_id(conn, REFRESH_TOKEN_TABLE, id_int)


async def delete_by_user_id(conn: AsyncConnection, user_id: str):
    return await delete_by_column(conn, REFRESH_TOKEN_TABLE, USER_ID, user_id)
