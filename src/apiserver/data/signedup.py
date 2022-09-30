from typing import Optional

from sqlalchemy.ext.asyncio import AsyncConnection

from apiserver.define.entities import SignedUp
from apiserver.data.source import Source, DataError
from apiserver.data.use import retrieve_by_unique, insert, exists_by_unique, retrieve_table, update_column_by_unique, \
    select_where
from apiserver.db import SIGNEDUP_TABLE
from apiserver.db.model import SU_FIRSTNAME, SU_LASTNAME, SU_EMAIL, SU_PHONE, SU_CONFIRMED
from apiserver.db.ops import DbError


__all__ = ['get_signedup_by_email', 'insert_su_row', 'signedup_exists', 'get_all_signedup']


def parse_signedup(signedup_dict: Optional[dict]) -> SignedUp:
    if signedup_dict is None:
        raise DataError("User does not exist.", "signedup_empty")
    return SignedUp.parse_obj(signedup_dict)


async def get_signedup_by_email(dsrc: Source, conn: AsyncConnection, email: str) -> SignedUp:
    signedup_row = await retrieve_by_unique(dsrc, conn, SIGNEDUP_TABLE, SU_EMAIL, email)
    return parse_signedup(signedup_row)


async def confirm_signup(dsrc: Source, conn: AsyncConnection, email: str):
    await update_column_by_unique(dsrc, conn, SIGNEDUP_TABLE, SU_CONFIRMED, True, SU_EMAIL, email)


async def get_all_signedup(dsrc: Source, conn: AsyncConnection) -> list[SignedUp]:
    all_signed_up = await select_where(dsrc, conn, SIGNEDUP_TABLE, SU_CONFIRMED, False)
    return [parse_signedup(su_dct) for su_dct in all_signed_up]


async def signedup_exists(dsrc: Source, email: str) -> bool:
    return await exists_by_unique(dsrc, SIGNEDUP_TABLE, SU_EMAIL, email)


async def insert_su_row(dsrc: Source, conn: AsyncConnection, su_row: dict):
    try:
        result = await insert(dsrc, conn, SIGNEDUP_TABLE, su_row)
    except DbError as e:
        raise DataError(f"{e.err_desc} from internal: {e.err_internal}", e.debug_key)
    return result
