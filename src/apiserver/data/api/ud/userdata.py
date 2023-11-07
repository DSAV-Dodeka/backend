from datetime import date
from typing import Any, Optional, Type

from sqlalchemy.ext.asyncio import AsyncConnection

from apiserver.lib.model.entities import UserData, SignedUp, IdInfo, UserNames
from auth.data.relational.user import (
    IdUserDataOps as AuthIdUserDataOps,
    IdUserData as AuthIdUserData,
    UserErrors,
)
from schema.model import (
    USERDATA_TABLE,
    USER_ID,
    UD_EMAIL,
    REGISTER_ID,
    UD_ACTIVE,
    UD_FIRSTNAME,
    UD_LASTNAME,
)
from store.db import (
    lit_model,
    retrieve_by_unique,
    insert_return_col,
    upsert_by_unique,
    update_column_by_unique,
    select_where,
    select_some_where,
)
from store.error import NoDataError, DataError, DbError


def parse_userdata(user_dict: Optional[dict[str, Any]]) -> UserData:
    if user_dict is None:
        raise NoDataError("UserData does not exist.", UserErrors.UD_EMPTY)
    return UserData.model_validate(user_dict)


def new_userdata(
    su: SignedUp, user_id: str, register_id: str, av40id: int, joined: date
) -> UserData:
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
) -> UserData:
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


class IdUserData(AuthIdUserData):
    attr_id_info: IdInfo

    def __init__(self, id_info: IdInfo):
        self.attr_id_info = id_info

    @classmethod
    def from_id_token(cls, id_token: dict[str, Any]) -> "IdUserData":
        id_info = IdInfo.model_validate(id_token)
        return IdUserData(id_info)

    def id_info(self) -> dict[str, Any]:
        return self.attr_id_info.model_dump()


async def get_userdata_by_id(conn: AsyncConnection, user_id: str) -> UserData:
    userdata_row = await retrieve_by_unique(conn, USERDATA_TABLE, USER_ID, user_id)
    return parse_userdata(userdata_row)


class IdUserDataOps(AuthIdUserDataOps):
    @classmethod
    async def get_id_userdata_by_id(
        cls, conn: AsyncConnection, user_id: str
    ) -> IdUserData:
        ud = await get_userdata_by_id(conn, user_id)

        return IdUserData(
            IdInfo(
                email=ud.email,
                name=f"{ud.firstname} {ud.lastname}",
                given_name=ud.firstname,
                family_name=ud.lastname,
                nickname=ud.callname,
                preferred_username=ud.callname,
                birthdate=ud.birthdate.isoformat(),
            )
        )

    @classmethod
    def get_type(cls) -> Type[IdUserData]:
        return IdUserData


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


async def insert_userdata(conn: AsyncConnection, userdata: UserData) -> str:
    try:
        user_id: str = await insert_return_col(
            conn, USERDATA_TABLE, lit_model(userdata), USER_ID
        )
    except DbError as e:
        raise DataError(f"{e.err_desc} from internal: {e.err_internal}", e.key)
    return user_id


async def upsert_userdata(conn: AsyncConnection, userdata: UserData) -> int:
    """Requires known id. Note that this cannot change any unique constraints, those must remain unaltered."""
    try:
        result = await upsert_by_unique(
            conn, USERDATA_TABLE, lit_model(userdata), USER_ID
        )
    except DbError as e:
        raise DataError(f"{e.err_desc} from internal: {e.err_internal}", e.key)
    return result


async def update_ud_email(conn: AsyncConnection, user_id: str, new_email: str) -> bool:
    try:
        count = await update_column_by_unique(
            conn, USERDATA_TABLE, UD_EMAIL, new_email, UD_EMAIL, user_id
        )
    except DbError as e:
        raise DataError(f"{e.err_desc} from internal: {e.err_internal}", e.key)
    return bool(count)


async def get_all_userdata(conn: AsyncConnection) -> list[UserData]:
    all_userdata = await select_where(conn, USERDATA_TABLE, UD_ACTIVE, True)
    return [parse_userdata(dict(ud_dct)) for ud_dct in all_userdata]


async def get_all_usernames(conn: AsyncConnection) -> list[UserNames]:
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
