import re
from datetime import date
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncConnection

from store.db import (
    retrieve_by_unique,
    insert_return_col,
    exists_by_unique,
    update_column_by_unique,
    upsert_by_unique,
    select_where,
    delete_by_column,
    select_some_two_where,
    insert,
    select_some_where,
    concat_column_by_unique_returning,
    select_some_join_where,
    DbError,
)
from schema.model import (
    USER_TABLE,
    USERDATA_TABLE,
    USER_ID,
    PASSWORD,
    REGISTER_ID,
    UD_FIRSTNAME,
    UD_LASTNAME,
    BIRTHDATE,
    UD_EMAIL,
    USER_EMAIL,
    UD_ACTIVE,
    SHOW_AGE,
    EASTER_EGG_TABLE,
    EE_EGG_ID,
    SCOPES,
)
from auth.data.schemad.user import UserOps as AuthUserOps
from apiserver.data.source import DataError, NoDataError
from apiserver.lib.model.entities import (
    User,
    SignedUp,
    UserData,
    BirthdayData,
    EasterEggData,
    UserScopeData,
    RawUserScopeData,
    ScopeData,
    UserID,
    UserNames,
)
from apiserver.lib.utilities import usp_hex, strip_edge, de_usp_hex

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
    return User.model_validate(user_dict)


def parse_userdata(user_dict: Optional[dict]) -> UserData:
    if user_dict is None:
        raise NoDataError("UserData does not exist.", "userdata_empty")
    return UserData.model_validate(user_dict)


def parse_scope_data(scope_dict: Optional[dict]) -> ScopeData:
    if scope_dict is None:
        raise NoDataError("ScopeData does not exist.", "scope_data_empty")

    return ScopeData.model_validate(scope_dict)


def parse_birthday_data(birthday_dict: Optional[dict]) -> BirthdayData:
    if birthday_dict is None:
        raise NoDataError("BirthdayData does not exist.", "birthday_data_empty")
    return BirthdayData.model_validate(birthday_dict)


def ignore_admin_member(scope: str):
    if scope == "admin" or scope == "member":
        return ""
    else:
        return scope


def parse_users_scopes_data(users_scope_dict: Optional[dict]) -> UserScopeData:
    if users_scope_dict is None:
        raise NoDataError("UserScopeData does not exist.", "user_scope_data_empty")
    raw_user_scope = RawUserScopeData.model_validate(users_scope_dict)
    name = raw_user_scope.firstname + " " + raw_user_scope.lastname
    scope_list = {
        ignore_admin_member(de_usp_hex(usph_scope))
        for usph_scope in raw_user_scope.scope.split(" ")
    }
    scope_list.discard("")
    return UserScopeData(
        name=name, user_id=raw_user_scope.user_id, scope=list(scope_list)
    )


def parse_easter_egg_data(easter_egg_dict: Optional[dict]) -> EasterEggData:
    if easter_egg_dict is None:
        raise NoDataError("BirthdayData does not exist.", "birthday_data_empty")
    return EasterEggData.model_validate(easter_egg_dict)


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


async def get_user_by_id(conn: AsyncConnection, user_id: str) -> User:
    user_row = await retrieve_by_unique(conn, USER_TABLE, USER_ID, user_id)
    return parse_user(user_row)


async def get_userdata_by_id(conn: AsyncConnection, user_id: str) -> UserData:
    userdata_row = await retrieve_by_unique(conn, USERDATA_TABLE, USER_ID, user_id)
    return parse_userdata(userdata_row)


async def get_userdata_by_email(conn: AsyncConnection, email: str) -> UserData:
    userdata_row = await retrieve_by_unique(conn, USERDATA_TABLE, UD_EMAIL, email)
    return parse_userdata(userdata_row)


async def get_userdata_by_register_id(
    conn: AsyncConnection, register_id: str
) -> UserData:
    userdata_row = await retrieve_by_unique(
        conn, USERDATA_TABLE, REGISTER_ID, register_id
    )
    return parse_userdata(userdata_row)


async def get_user_by_email(conn: AsyncConnection, user_email: str) -> User:
    user_row = await retrieve_by_unique(conn, USER_TABLE, USER_EMAIL, user_email)
    return parse_user(user_row)


async def update_password_file(conn: AsyncConnection, user_id: str, password_file: str):
    await update_column_by_unique(
        conn, USER_TABLE, PASSWORD, password_file, USER_ID, user_id
    )


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


async def insert_userdata(conn: AsyncConnection, userdata: UserData):
    try:
        user_id = await insert_return_col(
            conn, USERDATA_TABLE, userdata.model_dump(), USER_ID
        )
    except DbError as e:
        raise DataError(f"{e.err_desc} from internal: {e.err_internal}", e.debug_key)
    return user_id


async def upsert_userdata(conn: AsyncConnection, userdata: UserData):
    """Requires known id. Note that this cannot change any unique constraints, those must remain unaltered.
    """
    try:
        result = await upsert_by_unique(
            conn, USERDATA_TABLE, userdata.model_dump(), USER_ID
        )
    except DbError as e:
        raise DataError(f"{e.err_desc} from internal: {e.err_internal}", e.debug_key)
    return result


async def update_ud_email(conn: AsyncConnection, user_id: str, new_email: str) -> bool:
    try:
        count = await update_column_by_unique(
            conn, USERDATA_TABLE, UD_EMAIL, new_email, UD_EMAIL, user_id
        )
    except DbError as e:
        raise DataError(f"{e.err_desc} from internal: {e.err_internal}", e.debug_key)
    return bool(count)


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


async def get_all_userdata(conn: AsyncConnection) -> list[UserData]:
    all_userdata = await select_where(conn, USERDATA_TABLE, UD_ACTIVE, True)
    return [parse_userdata(dict(ud_dct)) for ud_dct in all_userdata]


async def get_all_user_ids(conn: AsyncConnection) -> list[UserID]:
    all_user_ids = await select_some_where(
        conn, USERDATA_TABLE, {USER_ID}, UD_ACTIVE, True
    )
    # This is the fastest way to parse in pure Python, although converting to dict is only slightly faster
    return [UserID(user_id=u_id_r[USER_ID]) for u_id_r in all_user_ids]


async def get_all_user_names(conn: AsyncConnection) -> list[UserNames]:
    all_user_names = await select_some_where(
        conn, USERDATA_TABLE, {USER_ID, UD_FIRSTNAME, UD_LASTNAME}, UD_ACTIVE, True
    )

    return [
        UserNames(
            user_id=u_names[USER_ID],
            firstname=u_names[UD_FIRSTNAME],
            lastname=u_names[UD_LASTNAME],
        )
        for u_names in all_user_names
    ]


async def get_all_birthdays(conn: AsyncConnection) -> list[BirthdayData]:
    all_birthdays = await select_some_two_where(
        conn,
        USERDATA_TABLE,
        {UD_FIRSTNAME, UD_LASTNAME, BIRTHDATE},
        UD_ACTIVE,
        True,
        SHOW_AGE,
        True,
    )
    return [parse_birthday_data(dict(bd_dct)) for bd_dct in all_birthdays]


async def get_all_users_scopes(conn: AsyncConnection) -> list[UserScopeData]:
    # user_id must be namespaced as it exists in both tables
    select_columns = {UD_FIRSTNAME, UD_LASTNAME, f"{USER_TABLE}.{USER_ID}", SCOPES}

    all_users_scopes = await select_some_join_where(
        conn,
        select_columns,
        USER_TABLE,
        USERDATA_TABLE,
        USER_ID,
        USER_ID,
        UD_ACTIVE,
        True,
    )

    return [
        parse_users_scopes_data(dict(u_ud_scope_dct))
        for u_ud_scope_dct in all_users_scopes
    ]


async def delete_user(conn: AsyncConnection, user_id: str):
    row_count = await delete_by_column(conn, USER_TABLE, USER_ID, user_id)
    if row_count == 0:
        raise NoDataError("User does not exist.", "user_empty")


async def add_scope(conn: AsyncConnection, user_id: str, new_scope: str):
    """Whitespace (according to Unicode standard) is removed and scope is added as usph
    """
    # We strip whitespace and other nasty characters from start and end
    stripped_scope = strip_edge(new_scope)
    # Space is added because we concatenate
    # We usp_hex to make weird Unicode characters visible easily
    scope_usph = " " + usp_hex(stripped_scope)

    try:
        final_scope: str = await concat_column_by_unique_returning(
            conn, USER_TABLE, SCOPES, SCOPES, scope_usph, USER_ID, user_id, SCOPES
        )
    except DbError as e:
        raise DataError(f"{e.err_desc} from internal: {e.err_internal}", e.debug_key)

    if final_scope is None:
        raise NoDataError(
            "No scope added, user most likely does not exist", "scope_not_added"
        )

    scope_values = final_scope.split(" ")
    if len(set(scope_values)) != len(scope_values):
        raise DataError("Scope already exists on scope", "scope_duplicate")


async def remove_scope(conn: AsyncConnection, user_id: str, old_scope: str):
    # Space is added because we concatenate
    scope_usph = usp_hex(old_scope)

    try:
        data_list = await select_some_where(
            conn, USER_TABLE, {SCOPES}, USER_ID, user_id
        )
    except DbError as e:
        raise DataError(f"{e.err_desc} from internal: {e.err_internal}", e.debug_key)

    # With 'where USER_ID = user_id', the result should only contain one dict.
    # Maybe in the future we can make the user_id attribute a list to bulk remove roles.
    # For example a button to more easily change the board -> Remove role from old board
    if len(data_list) != 1:
        raise DataError(
            "No scope removed, user most likely does not exist", "scope_not_removed"
        )

    scope_data = parse_scope_data(dict(data_list[0]))

    scope_string = scope_data.scope
    scope_list = scope_string.split(" ")

    try:
        scope_list.remove(scope_usph)
    except ValueError:
        raise DataError("Scope does not exists on scope", "scope_nonexistent")

    result = " ".join([str(scope) for scope in scope_list])

    try:
        await update_column_by_unique(
            conn, USER_TABLE, SCOPES, result, USER_ID, user_id
        )
    except DbError as e:
        raise DataError(f"{e.err_desc} from internal: {e.err_internal}", e.debug_key)


async def get_easter_eggs_count(conn: AsyncConnection, user_id: str):
    easter_eggs_found = await select_some_where(
        conn,
        EASTER_EGG_TABLE,
        EE_EGG_ID,
        USER_ID,
        user_id,
    )

    return [parse_easter_egg_data(dict(eed_dct)) for eed_dct in easter_eggs_found]
