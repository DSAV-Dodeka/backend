from typing import Protocol

from sqlalchemy.ext.asyncio import AsyncConnection

from auth.data.relational.entities import SavedRefreshToken


class RefreshOps(Protocol):
    @classmethod
    async def insert_refresh_row(
        cls, conn: AsyncConnection, refresh: SavedRefreshToken
    ) -> int: ...

    @classmethod
    async def get_refresh_by_id(
        cls, conn: AsyncConnection, id_int: int
    ) -> SavedRefreshToken: ...

    @classmethod
    async def delete_family(cls, conn: AsyncConnection, family_id: str) -> int: ...

    @classmethod
    async def delete_refresh_by_id(cls, conn: AsyncConnection, id_int: int) -> int: ...

    @classmethod
    async def delete_by_user_id(cls, conn: AsyncConnection, user_id: str) -> int: ...
