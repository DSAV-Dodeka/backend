from typing import Protocol

from sqlalchemy.ext.asyncio import AsyncConnection

from auth.data.schemad.entities import User


class UserOps(Protocol):
    @classmethod
    async def get_user_by_id(cls, conn: AsyncConnection, user_id: str) -> User:
        ...

    @classmethod
    async def get_user_by_email(cls, conn: AsyncConnection, email: str) -> User:
        ...
