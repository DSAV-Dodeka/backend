from typing import Optional
from datetime import date

from sqlalchemy.engine import CursorResult, Row
from sqlalchemy.ext.asyncio import AsyncConnection

from apiserver.define.entities import User, SignedUp, UserData
from apiserver.utilities import usp_hex
from apiserver.data.source import Source, DataError
from apiserver.data.use import retrieve_by_id, retrieve_by_unique, upsert_by_id, insert_return_id, \
    double_insert_transaction, exists_by_unique
from apiserver.db import USER_TABLE, USERDATA_TABLE
from apiserver.db.model import USERNAME, PASSWORD, REGISTER_ID, SCOPES
from apiserver.db.ops import DbError


__all__ = ['get_user_by_id', 'upsert_user', 'create_user', 'user_exists']


def parse_user(user_dict: Optional[dict]) -> User:
    if user_dict is None:
        raise DataError("User does not exist.", "user_empty")
    return User.parse_obj(user_dict)


def parse_userdata(user_dict: Optional[dict]) -> UserData:
    if user_dict is None:
        raise DataError("UserData does not exist.", "userdata_empty")
    return UserData.parse_obj(user_dict)


async def user_exists(dsrc: Source, user_usph: str) -> bool:
    return await exists_by_unique(dsrc, USER_TABLE, USERNAME, user_usph)


async def get_user_by_id(dsrc: Source, conn: AsyncConnection, id_int: int) -> User:
    user_row = await retrieve_by_id(dsrc, conn, USER_TABLE, id_int)
    return parse_user(user_row)


async def get_userdata_by_register_id(dsrc: Source, register_id: str) -> UserData:
    userdata_row = await retrieve_by_unique(dsrc, USERDATA_TABLE, REGISTER_ID, register_id)
    return parse_userdata(userdata_row)


async def get_user_by_usph(dsrc: Source, user_usph: str) -> User:
    user_row = await retrieve_by_unique(dsrc, USER_TABLE, USERNAME, user_usph)
    return parse_user(user_row)


async def upsert_user(dsrc: Source, user: User):
    try:
        result = await upsert_by_id(dsrc, USER_TABLE, user.dict())
    except DbError as e:
        raise DataError(f"{e.err_desc} from internal: {e.err_internal}", e.debug_key)
    return result


async def insert_return_user_id(dsrc: Source, user_row: dict):
    try:
        result = await insert_return_id(dsrc, USER_TABLE, user_row)
    except DbError as e:
        raise DataError(f"{e.err_desc} from internal: {e.err_internal}", e.debug_key)
    return result


async def new_user(dsrc: Source, signed_up: SignedUp, register_id: str, av40id: int, joined: date):
    email_usph = usp_hex(signed_up.email)
    user_row = create_user(email_usph, "")
    user_data_row = UserData(id=0, active=True, registerid=register_id, firstname=signed_up.firstname,
                             lastname=signed_up.lastname, email=signed_up.email, phone=signed_up.phone, av40id=av40id,
                             joined=joined, registered=False).dict()
    try:
        result = await double_insert_transaction(dsrc, USER_TABLE, user_row, USERDATA_TABLE, user_data_row)
    except DbError as e:
        raise DataError(f"{e.err_desc} from internal: {e.err_internal}", e.debug_key)
    return result


async def upsert_userdata(dsrc: Source, userdata: UserData):
    """ Requires known id. Note that this cannot change any unique constraints, those must remain unaltered."""
    try:
        result = await upsert_by_id(dsrc, USERDATA_TABLE, userdata.dict())
    except DbError as e:
        raise DataError(f"{e.err_desc} from internal: {e.err_internal}", e.debug_key)
    return result


async def get_user_scope_password(dsrc: Source, user_usph) -> (str, str):
    user = await get_user_by_usph(dsrc, user_usph)
    return user.scope, user.password_file


def create_user(ups_hex, password_file) -> dict:
    return {
        USERNAME: ups_hex,
        PASSWORD: password_file,
        SCOPES: "none"
    }
