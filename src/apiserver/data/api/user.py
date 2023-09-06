import re
from datetime import date
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncConnection

from store.db import (
    retrieve_by_unique,
    insert_return_col,
    exists_by_unique,
    update_column_by_unique,
    delete_by_column,
    insert,
    select_some_where,
    DbError,
)
from schema.model import (
    USER_TABLE,
    USERDATA_TABLE,
    USER_ID,
    PASSWORD,
    USER_EMAIL,
    UD_ACTIVE,
)
from auth.data.schemad.user import (
    UserOps as AuthUserOps,
)
from store.error import DataError, NoDataError
from apiserver.lib.model.entities import (
    User,
    SignedUp,
    UserID,
)
from apiserver.lib.utilities import usp_hex
from apiserver.data.api.ud.userdata import new_userdata, insert_userdata

__all__ = [
    "get_user_by_id",
    "user_exists",
    "user_exists",
    "get_user_by_email",
    "insert_user",
    "insert_return_user_id",
    "gen_id_name",
    "new_user",
    "UserOps",
]


def parse_user(user_dict: Optional[dict]) -> User:
    if user_dict is None:
        raise NoDataError("User does not exist.", "user_empty")
    return User.model_validate(user_dict)


async def user_exists(conn: AsyncConnection, user_email: str) -> bool:
    return await exists_by_unique(conn, USER_TABLE, USER_EMAIL, user_email)


class UserOps(AuthUserOps):
    @classmethod
    async def get_user_by_id(cls, conn: AsyncConnection, user_id: str) -> User:
        user_row = await retrieve_by_unique(conn, USER_TABLE, USER_ID, user_id)
        return parse_user(user_row)

    @classmethod
    async def get_user_by_email(cls, conn: AsyncConnection, user_email: str) -> User:
        user_row = await retrieve_by_unique(conn, USER_TABLE, USER_EMAIL, user_email)
        return parse_user(user_row)

    @classmethod
    async def update_password_file(
        cls, conn: AsyncConnection, user_id: str, password_file: str
    ) -> int:
        return await update_column_by_unique(
            conn, USER_TABLE, PASSWORD, password_file, USER_ID, user_id
        )


async def get_user_by_id(conn: AsyncConnection, user_id: str) -> User:
    user_row = await retrieve_by_unique(conn, USER_TABLE, USER_ID, user_id)
    return parse_user(user_row)


async def get_user_by_email(conn: AsyncConnection, user_email: str) -> User:
    user_row = await retrieve_by_unique(conn, USER_TABLE, USER_EMAIL, user_email)
    return parse_user(user_row)


async def insert_user(conn: AsyncConnection, user: User):
    user_row: dict = user.model_dump(exclude={"user_id"})
    try:
        await insert(conn, USER_TABLE, user_row)
    except DbError as e:
        raise DataError(f"{e.err_desc} from internal: {e.err_internal}", e.debug_key)


async def insert_return_user_id(conn: AsyncConnection, user: User) -> str:
    user_row: dict = user.model_dump(exclude={"id", "user_id"})
    try:
        user_id = await insert_return_col(conn, USER_TABLE, user_row, USER_ID)
    except DbError as e:
        raise DataError(f"{e.err_desc} from internal: {e.err_internal}", e.debug_key)
    return user_id


whitespace_pattern = re.compile(r"\s+")


def gen_id_name(first_name: str, last_name: str):
    id_name_str = f"{first_name}_{last_name}".lower()
    id_name_str = re.sub(whitespace_pattern, "_", id_name_str)
    return usp_hex(id_name_str)


async def new_user(
    conn: AsyncConnection,
    signed_up: SignedUp,
    register_id: str,
    av40id: int,
    joined: date,
):
    id_name = gen_id_name(signed_up.firstname, signed_up.lastname)

    user = User(id_name=id_name, email=signed_up.email, password_file="")
    user_id = await insert_return_user_id(conn, user)
    userdata = new_userdata(signed_up, user_id, register_id, av40id, joined)

    await insert_userdata(conn, userdata)

    return user_id


async def update_user_email(
    conn: AsyncConnection, user_id: str, new_email: str
) -> bool:
    try:
        count = await update_column_by_unique(
            conn, USER_TABLE, USER_EMAIL, new_email, USER_ID, user_id
        )
    except DbError as e:
        raise DataError(f"{e.err_desc} from internal: {e.err_internal}", e.debug_key)
    return bool(count)


async def get_all_user_ids(conn: AsyncConnection) -> list[UserID]:
    all_user_ids = await select_some_where(
        conn, USERDATA_TABLE, {USER_ID}, UD_ACTIVE, True
    )
    # This is the fastest way to parse in pure Python, although converting to dict is only slightly faster
    return [UserID(user_id=u_id_r[USER_ID]) for u_id_r in all_user_ids]


async def delete_user(conn: AsyncConnection, user_id: str):
    row_count = await delete_by_column(conn, USER_TABLE, USER_ID, user_id)
    if row_count == 0:
        raise NoDataError("User does not exist.", "user_empty")
