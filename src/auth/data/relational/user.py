from enum import StrEnum
from typing import Any, Protocol, Self, Type, TypeAlias

from sqlalchemy.ext.asyncio import AsyncConnection

from auth.data.relational.entities import User


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


class IdUserData(Protocol):
    @classmethod
    def from_id_token(cls, id_token: dict[str, Any]) -> Self: ...

    """id_userdata_from_token"""

    def id_info(self) -> dict[str, Any]: ...


class IdUserDataOps(Protocol):
    @classmethod
    async def get_id_userdata_by_id(
        cls, conn: AsyncConnection, user_id: str
    ) -> IdUserData:
        """Throws NoDataError if user does not exist."""
        ...

    @classmethod
    def get_type(cls) -> Type[IdUserData]: ...


# class IdUserDataOps(Protocol, Generic[IdUserDataT]):
#     @classmethod
#     async def get_id_userdata_by_id(cls, conn: AsyncConnection, user_id: str) -> IdUserDataT:
#         """Throws NoDataError if user does not exist."""
#         ...

#     @classmethod
#     def id_info_from_id_userdata(cls, ud: IdUserDataT) -> dict[str, Any]: ...


#     @classmethod
#     def id_userdata_from_token(cls, id_token: dict[str, Any]) -> IdUserDataT: ...
