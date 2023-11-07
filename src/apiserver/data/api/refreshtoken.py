from typing import Any, Optional

from sqlalchemy.ext.asyncio import AsyncConnection

from store.db import (
    lit_dict,
    retrieve_by_id,
    insert_return_col,
    delete_by_column,
    delete_by_id,
)
from schema.model import REFRESH_TOKEN_TABLE, FAMILY_ID, USER_ID
from store.error import NoDataError
from auth.data.relational.refresh import RefreshOps as AuthRefreshOps
from auth.data.relational.entities import SavedRefreshToken


def parse_refresh(refresh_dict: Optional[dict[str, Any]]) -> SavedRefreshToken:
    if refresh_dict is None:
        raise NoDataError("Refresh Token does not exist.", "refresh_empty")
    return SavedRefreshToken.model_validate(refresh_dict)


class RefreshOps(AuthRefreshOps):
    @classmethod
    async def insert_refresh_row(
        cls, conn: AsyncConnection, refresh: SavedRefreshToken
    ) -> int:
        refresh_row = lit_dict(refresh.model_dump(exclude={"id"}))
        refresh_id: int = await insert_return_col(
            conn, REFRESH_TOKEN_TABLE, refresh_row, "id"
        )
        return refresh_id

    @classmethod
    async def get_refresh_by_id(
        cls, conn: AsyncConnection, id_int: int
    ) -> SavedRefreshToken:
        refresh_row = await retrieve_by_id(conn, REFRESH_TOKEN_TABLE, id_int)
        return parse_refresh(refresh_row)

    @classmethod
    async def delete_family(cls, conn: AsyncConnection, family_id: str) -> int:
        return await delete_by_column(conn, REFRESH_TOKEN_TABLE, FAMILY_ID, family_id)

    @classmethod
    async def delete_refresh_by_id(cls, conn: AsyncConnection, id_int: int) -> int:
        return await delete_by_id(conn, REFRESH_TOKEN_TABLE, id_int)

    @classmethod
    async def delete_by_user_id(cls, conn: AsyncConnection, user_id: str) -> int:
        return await delete_by_column(conn, REFRESH_TOKEN_TABLE, USER_ID, user_id)
