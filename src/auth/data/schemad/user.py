from typing import Protocol, Type

from sqlalchemy.ext.asyncio import AsyncConnection

from auth.core.model import IdInfo
from auth.data.schemad.entities import User, UserData


class UserOps(Protocol):
    @classmethod
    async def get_user_by_id(cls, conn: AsyncConnection, user_id: str) -> User:
        ...

    @classmethod
    async def get_user_by_email(cls, conn: AsyncConnection, email: str) -> User:
        ...

    @classmethod
    async def update_password_file(
        cls, conn: AsyncConnection, user_id: str, password_file: str
    ) -> int:
        ...


class UserDataOps(Protocol):
    @classmethod
    async def get_userdata_by_id(cls, conn: AsyncConnection, user_id: str) -> UserData:
        """Throws NoDataError if user does not exist."""
        ...

    @classmethod
    def id_info_from_ud(cls, ud: UserData) -> IdInfo:
        ...

    @classmethod
    def id_info_type(cls) -> Type[IdInfo]:
        ...
