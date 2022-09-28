from typing import Optional

from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncConnection

from apiserver.data.use import retrieve_by_id, get_largest_where, update_column_by_unique
from apiserver.define.entities import TokenKey, SymmetricKey, JWKSRow
from apiserver.data.source import Source, DataError
from apiserver.db import KEY_TABLE, JWK_TABLE
from apiserver.db.model import JWK_VALUE, KEY_ID, KEY_ISSUED, KEY_USE
from apiserver.auth.key_util import new_ed448_keypair, new_symmetric_key


async def get_newest_symmetric(dsrc: Source, conn: AsyncConnection) -> tuple[str, str]:
    results = await get_largest_where(dsrc, conn, KEY_TABLE, KEY_ID, KEY_USE, "enc", KEY_ISSUED, 2)
    return results[0], results[1]


async def get_newest_pem(dsrc: Source, conn: AsyncConnection) -> str:
    return (await get_largest_where(dsrc, conn, KEY_TABLE, KEY_ID, KEY_USE, "sig", KEY_ISSUED, 1))[0]


async def update_jwk(dsrc: Source, conn: AsyncConnection, encrypted_jwk_set: str) -> int:
    return await update_column_by_unique(dsrc, conn, JWK_TABLE, JWK_VALUE, encrypted_jwk_set, "id", 1)


async def get_jwk(dsrc: Source, conn: AsyncConnection) -> str:
    row_dict = await retrieve_by_id(dsrc, conn, JWK_TABLE, 1)
    if row_dict is None:
        raise DataError(message=f"JWK Set missing.", key="missing_jwks")
    return JWKSRow.parse_obj(row_dict).encrypted_value

