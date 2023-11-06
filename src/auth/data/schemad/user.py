from enum import StrEnum
from typing import Generic, Protocol, Type

from sqlalchemy.ext.asyncio import AsyncConnection

from auth.data.schemad.entities import IdInfoT, User, UserDataT


class UserErrors(StrEnum):
    U_EMPTY = "user_empty"
    UD_EMPTY = "userdata_empty"


class UserOps(Protocol):
    @classmethod
    async def get_user_by_id(cls, conn: AsyncConnection, user_id: str) -> User:
        """THROWS NoDataError if user does not exist, with key U_EMPTY."""
        ...

    @classmethod
    async def get_user_by_email(cls, conn: AsyncConnection, email: str) -> User: ...

    @classmethod
    async def update_password_file(
        cls, conn: AsyncConnection, user_id: str, password_file: str
    ) -> int: ...


class UserDataOps(Protocol, Generic[UserDataT, IdInfoT]):
    @classmethod
    async def get_userdata_by_id(cls, conn: AsyncConnection, user_id: str) -> UserDataT:
        """Throws NoDataError if user does not exist."""
        ...

    @classmethod
    def id_info_from_ud(cls, ud: UserDataT) -> IdInfoT: ...

    @classmethod
    def id_info_type(cls) -> Type[IdInfoT]: ...
