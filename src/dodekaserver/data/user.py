from typing import Optional
from datetime import date

from dodekaserver.define.entities import User, SignedUp, UserData
from dodekaserver.utilities import usp_hex
from dodekaserver.data.source import Source, DataError
from dodekaserver.data.use import retrieve_by_id, retrieve_by_unique, upsert_by_id, insert_return_id, \
    double_insert_transaction
from dodekaserver.db import USER_TABLE, USERDATA_TABLE
from dodekaserver.db.model import USERNAME, PASSWORD
from dodekaserver.db.ops import DbError


__all__ = ['get_user_by_id', 'upsert_user_row', 'create_user']


def parse_user(user_dict: Optional[dict]) -> User:
    if user_dict is None:
        raise DataError("User does not exist.", "user_empty")
    return User.parse_obj(user_dict)


async def get_user_by_id(dsrc: Source, id_int: int) -> User:
    user_row = await retrieve_by_id(dsrc, USER_TABLE, id_int)
    return parse_user(user_row)


async def get_user_data_by_id(dsrc: Source, id_int: int) -> User:
    user_row = await retrieve_by_id(dsrc, USER_TABLE, id_int)
    return parse_user(user_row)


async def get_user_by_usph(dsrc: Source, user_usph: str) -> User:
    user_row = await retrieve_by_unique(dsrc, USER_TABLE, USERNAME, user_usph)
    return parse_user(user_row)


async def upsert_user_row(dsrc: Source, user_row: dict):
    try:
        result = await upsert_by_id(dsrc, USER_TABLE, user_row)
    except DbError as e:
        raise DataError(f"{e.err_desc} from internal: {e.err_internal}", e.debug_key)
    return result


async def insert_return_user_id(dsrc: Source, user_row: dict):
    try:
        result = await insert_return_id(dsrc, USER_TABLE, user_row)
    except DbError as e:
        raise DataError(f"{e.err_desc} from internal: {e.err_internal}", e.debug_key)
    return result


async def new_user(dsrc: Source, signed_up: SignedUp, av40id: int, joined: date):
    email_usph = usp_hex(signed_up.email)
    user_row = create_user(email_usph, "")
    user_data_row = UserData(id=0, active=True, firstname=signed_up.firstname, lastname=signed_up.lastname,
                             email=signed_up.email, phone=signed_up.phone, av40id=av40id, joined=joined).dict()
    try:
        result = await double_insert_transaction(dsrc, USER_TABLE, user_row, USERDATA_TABLE, user_data_row)
    except DbError as e:
        raise DataError(f"{e.err_desc} from internal: {e.err_internal}", e.debug_key)
    return result


async def get_user_password_file(dsrc: Source, user_usph):
    return (await get_user_by_usph(dsrc, user_usph)).password_file


def create_user(ups_hex, password_file) -> dict:
    return {
        USERNAME: ups_hex,
        PASSWORD: password_file
    }
