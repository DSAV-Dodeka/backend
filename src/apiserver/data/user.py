import re
from typing import Optional
from datetime import date

from sqlalchemy.engine import CursorResult, Row
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncTransaction

from apiserver.define.entities import User, SignedUp, UserData, BirthdayData
from apiserver.utilities import usp_hex
from apiserver.data.source import Source, DataError, NoDataError
from apiserver.data.use import (
    retrieve_by_unique,
    insert_return_col,
    exists_by_unique,
    update_column_by_unique,
    upsert_by_unique,
    select_where,
    delete_by_column,
    select_some_where,
)
from apiserver.db import USER_TABLE, USERDATA_TABLE
from apiserver.db.model import (
    USER_ID,
    PASSWORD,
    REGISTER_ID,
    UD_FIRSTNAME,
    UD_LASTNAME,
    BIRTHDATE,
    UD_EMAIL,
    USER_EMAIL,
    UD_ACTIVE,
)
from apiserver.db.ops import DbError

__all__ = ["get_user_by_id", "user_exists", "get_userdata_by_email"]


def parse_user(user_dict: Optional[dict]) -> User:
    if user_dict is None:
        raise NoDataError("User does not exist.", "user_empty")
    return User.parse_obj(user_dict)


def parse_userdata(user_dict: Optional[dict]) -> UserData:
    if user_dict is None:
        raise NoDataError("UserData does not exist.", "userdata_empty")
    return UserData.parse_obj(user_dict)


def parse_birthday_data(birthday_dict: Optional[dict]) -> BirthdayData:
    if birthday_dict is None:
        raise NoDataError("BirthdayData does not exist.", "birthday_data_empty")
    return BirthdayData.parse_obj(birthday_dict)


async def user_exists(dsrc: Source, conn: AsyncConnection, user_email: str) -> bool:
    return await exists_by_unique(dsrc, conn, USER_TABLE, USER_EMAIL, user_email)


async def get_user_by_id(dsrc: Source, conn: AsyncConnection, user_id: str) -> User:
    user_row = await retrieve_by_unique(dsrc, conn, USER_TABLE, USER_ID, user_id)
    return parse_user(user_row)


async def get_userdata_by_id(
    dsrc: Source, conn: AsyncConnection, user_id: str
) -> UserData:
    userdata_row = await retrieve_by_unique(
        dsrc, conn, USERDATA_TABLE, USER_ID, user_id
    )
    return parse_userdata(userdata_row)


async def get_userdata_by_email(
    dsrc: Source, conn: AsyncConnection, email: str
) -> UserData:
    userdata_row = await retrieve_by_unique(dsrc, conn, USERDATA_TABLE, UD_EMAIL, email)
    return parse_userdata(userdata_row)


async def get_userdata_by_register_id(
    dsrc: Source, conn: AsyncConnection, register_id: str
) -> UserData:
    userdata_row = await retrieve_by_unique(
        dsrc, conn, USERDATA_TABLE, REGISTER_ID, register_id
    )
    return parse_userdata(userdata_row)


# async def userdata_registered_by_email(
#     dsrc: Source, conn: AsyncConnection, email: str
# ) -> bool:
#     result = await fetch_column_by_unique(
#         dsrc, conn, USERDATA_TABLE, USER_REGISTERED, UD_EMAIL, email
#     )
#     return result if result is True else False


async def get_user_by_email(
    dsrc: Source, conn: AsyncConnection, user_email: str
) -> User:
    user_row = await retrieve_by_unique(dsrc, conn, USER_TABLE, USER_EMAIL, user_email)
    return parse_user(user_row)


async def update_password_file(
    dsrc: Source, conn: AsyncConnection, user_id: str, password_file: str
):
    await update_column_by_unique(
        dsrc, conn, USER_TABLE, PASSWORD, password_file, USER_ID, user_id
    )


async def insert_return_user_id(dsrc: Source, conn: AsyncConnection, user: User) -> str:
    user_row: dict = user.dict(exclude={"id", "user_id"})
    try:
        user_id = await insert_return_col(dsrc, conn, USER_TABLE, user_row, USER_ID)
    except DbError as e:
        raise DataError(f"{e.err_desc} from internal: {e.err_internal}", e.debug_key)
    return user_id


whitespace_pattern = re.compile(r"\s+")


def gen_id_name(first_name: str, last_name: str):
    id_name_str = f"{first_name}_{last_name}".lower()
    id_name_str = re.sub(whitespace_pattern, "_", id_name_str)
    return usp_hex(id_name_str)


async def new_user(
    dsrc: Source,
    conn: AsyncConnection,
    signed_up: SignedUp,
    register_id: str,
    av40id: int,
    joined: date,
):
    id_name = gen_id_name(signed_up.firstname, signed_up.lastname)

    user = User(id_name=id_name, email=signed_up.email, password_file="")
    user_id = await insert_return_user_id(dsrc, conn, user)

    userdata = UserData(
        user_id=user_id,
        active=True,
        registerid=register_id,
        firstname=signed_up.firstname,
        lastname=signed_up.lastname,
        email=signed_up.email,
        phone=signed_up.phone,
        av40id=av40id,
        joined=joined,
        registered=False,
    )
    await insert_userdata(dsrc, conn, userdata)

    return user_id


async def insert_userdata(dsrc: Source, conn: AsyncConnection, userdata: UserData):
    try:
        user_id = await insert_return_col(
            dsrc, conn, USERDATA_TABLE, userdata.dict(), USER_ID
        )
    except DbError as e:
        raise DataError(f"{e.err_desc} from internal: {e.err_internal}", e.debug_key)
    return user_id


async def upsert_userdata(dsrc: Source, conn: AsyncConnection, userdata: UserData):
    """Requires known id. Note that this cannot change any unique constraints, those must remain unaltered.
    """
    try:
        result = await upsert_by_unique(
            dsrc, conn, USERDATA_TABLE, userdata.dict(), USER_ID
        )
    except DbError as e:
        raise DataError(f"{e.err_desc} from internal: {e.err_internal}", e.debug_key)
    return result


async def update_ud_email(
    dsrc: Source, conn: AsyncConnection, user_id: str, new_email: str
) -> bool:
    try:
        count = await update_column_by_unique(
            dsrc, conn, USERDATA_TABLE, UD_EMAIL, new_email, UD_EMAIL, user_id
        )
    except DbError as e:
        raise DataError(f"{e.err_desc} from internal: {e.err_internal}", e.debug_key)
    return bool(count)


async def update_user_email(
    dsrc: Source, conn: AsyncConnection, user_id: str, new_email: str
) -> bool:
    try:
        count = await update_column_by_unique(
            dsrc, conn, USER_TABLE, USER_EMAIL, new_email, USER_ID, user_id
        )
    except DbError as e:
        raise DataError(f"{e.err_desc} from internal: {e.err_internal}", e.debug_key)
    return bool(count)


async def get_all_userdata(dsrc: Source, conn: AsyncConnection) -> list[UserData]:
    all_userdata = await select_where(dsrc, conn, USERDATA_TABLE, UD_ACTIVE, True)
    return [parse_userdata(ud_dct) for ud_dct in all_userdata]


async def get_all_birthdays(dsrc: Source, conn: AsyncConnection) -> list[BirthdayData]:
    all_birthdays = await select_some_where(
        dsrc,
        conn,
        USERDATA_TABLE,
        {UD_FIRSTNAME, UD_LASTNAME, BIRTHDATE},
        UD_ACTIVE,
        True,
    )
    return [parse_birthday_data(ud_dct) for ud_dct in all_birthdays]


async def delete_user(dsrc: Source, conn: AsyncConnection, user_id: str):
    await delete_by_column(dsrc, conn, USER_TABLE, USER_ID, user_id)
