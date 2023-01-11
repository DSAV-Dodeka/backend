import re
from typing import Optional
from datetime import date

from sqlalchemy.ext.asyncio import AsyncConnection

from apiserver.define.entities import User, SignedUp, UserData, BirthdayData, EasterEggData
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
    select_some_two_where,
    insert, select_some_where,
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
    SHOW_AGE, EASTER_EGG_TABLE, EE_EGG_ID,
)
from apiserver.db.ops import DbError

__all__ = [
    "get_user_by_id",
    "user_exists",
    "get_userdata_by_email",
    "new_userdata",
    "finished_userdata",
    "user_exists",
    "get_userdata_by_id",
    "get_userdata_by_register_id",
    "get_user_by_email",
    "update_password_file",
    "insert_user",
    "insert_return_user_id",
    "gen_id_name",
    "new_user",
]


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


def parse_easter_egg_data(easter_egg_dict: Optional[dict]) -> EasterEggData:
    if easter_egg_dict is None:
        raise NoDataError("BirthdayData does not exist.", "birthday_data_empty")
    return EasterEggData.parse_obj(easter_egg_dict)


def new_userdata(
        su: SignedUp, user_id: str, register_id: str, av40id: int, joined: date
):
    return UserData(
        user_id=user_id,
        active=True,
        registerid=register_id,
        firstname=su.firstname,
        lastname=su.lastname,
        email=su.email,
        phone=su.phone,
        av40id=av40id,
        joined=joined,
        registered=False,
        showage=False,
    )


def finished_userdata(
        ud: UserData, callname: str, eduinstitution: str, birthdate: date, show_age: bool
):
    return UserData(
        user_id=ud.user_id,
        firstname=ud.firstname,
        lastname=ud.lastname,
        callname=callname,
        email=ud.email,
        phone=ud.phone,
        av40id=ud.av40id,
        joined=ud.joined,
        eduinstitution=eduinstitution,
        birthdate=birthdate,
        registerid=ud.registerid,
        active=True,
        registered=True,
        showage=show_age,
    )


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


async def insert_user(dsrc: Source, conn: AsyncConnection, user: User) -> str:
    user_row: dict = user.dict(exclude={"user_id"})
    try:
        user_id = await insert(dsrc, conn, USER_TABLE, user_row)
    except DbError as e:
        raise DataError(f"{e.err_desc} from internal: {e.err_internal}", e.debug_key)
    return user_id


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
    userdata = new_userdata(signed_up, user_id, register_id, av40id, joined)

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
    all_birthdays = await select_some_two_where(
        dsrc,
        conn,
        USERDATA_TABLE,
        {UD_FIRSTNAME, UD_LASTNAME, BIRTHDATE},
        UD_ACTIVE,
        True,
        SHOW_AGE,
        True,
    )
    return [parse_birthday_data(bd_dct) for bd_dct in all_birthdays]


async def delete_user(dsrc: Source, conn: AsyncConnection, user_id: str):
    row_count = await delete_by_column(dsrc, conn, USER_TABLE, USER_ID, user_id)
    if row_count == 0:
        raise NoDataError("User does not exist.", "user_empty")


async def get_easter_eggs_count(dsrc: Source, conn: AsyncConnection, user_id: str):
    easter_eggs_found = await select_some_where(
        dsrc,
        conn,
        EASTER_EGG_TABLE,
        EE_EGG_ID,
        USER_ID,
        user_id,
    )

    return [parse_easter_egg_data(eed_dct) for eed_dct in easter_eggs_found]


async def found_easter_egg(dsrc: Source, conn: AsyncConnection, user_id: str, egg_id: str):
    # Insert into database?

    # await insert_value_where(
    #     dsrc,
    #     conn,
    #     EASTER_EGG_TABLE,
    #     EE_EGG_ID,
    #     egg_id,
    #     USER_ID,
    #     user_id,
    # )

    return None
