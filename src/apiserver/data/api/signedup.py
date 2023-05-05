from typing import Optional

from sqlalchemy.ext.asyncio import AsyncConnection

from apiserver.lib.model.entities import SignedUp
from apiserver.data.db.model import (
    SIGNEDUP_TABLE,
    SU_EMAIL,
    SU_CONFIRMED,
)
from apiserver.data.db.ops import (
    DbError,
    retrieve_by_unique,
    insert,
    exists_by_unique,
    update_column_by_unique,
    select_where,
    delete_by_column,
)
from apiserver.data.source import DataError

__all__ = [
    "get_signedup_by_email",
    "insert_su_row",
    "signedup_exists",
    "get_all_signedup",
    "delete_signedup",
]


def parse_signedup(signedup_dict: Optional[dict]) -> SignedUp:
    if signedup_dict is None:
        raise DataError("User does not exist.", "signedup_empty")
    return SignedUp.parse_obj(signedup_dict)


async def get_signedup_by_email(conn: AsyncConnection, email: str) -> SignedUp:
    signedup_row = await retrieve_by_unique(conn, SIGNEDUP_TABLE, SU_EMAIL, email)
    return parse_signedup(signedup_row)


async def confirm_signup(conn: AsyncConnection, email: str):
    await update_column_by_unique(
        conn, SIGNEDUP_TABLE, SU_CONFIRMED, True, SU_EMAIL, email
    )


async def get_all_signedup(conn: AsyncConnection) -> list[SignedUp]:
    all_signed_up = await select_where(conn, SIGNEDUP_TABLE, SU_CONFIRMED, False)
    return [parse_signedup(dict(su_dct)) for su_dct in all_signed_up]


async def signedup_exists(conn: AsyncConnection, email: str) -> bool:
    return await exists_by_unique(conn, SIGNEDUP_TABLE, SU_EMAIL, email)


async def insert_su_row(conn: AsyncConnection, su_row: dict):
    try:
        result = await insert(conn, SIGNEDUP_TABLE, su_row)
    except DbError as e:
        raise DataError(f"{e.err_desc} from internal: {e.err_internal}", e.debug_key)
    return result


async def delete_signedup(conn: AsyncConnection, email: str):
    await delete_by_column(conn, SIGNEDUP_TABLE, SU_EMAIL, email)
