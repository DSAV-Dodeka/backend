from sqlalchemy.ext.asyncio import AsyncConnection

from apiserver.data.use import (
    retrieve_by_id,
    get_largest_where,
    update_column_by_unique,
    insert,
)
from apiserver.define.entities import JWKSRow
from apiserver.data.source import Source, DataError
from apiserver.db import KEY_TABLE, JWK_TABLE
from apiserver.db.model import JWK_VALUE, KEY_ID, KEY_ISSUED, KEY_USE


async def get_newest_symmetric(dsrc: Source, conn: AsyncConnection) -> tuple[str, str]:
    results = await get_largest_where(
        dsrc, conn, KEY_TABLE, KEY_ID, KEY_USE, "enc", KEY_ISSUED, 2
    )
    return results[0], results[1]


async def get_newest_pem(dsrc: Source, conn: AsyncConnection) -> str:
    return (
        await get_largest_where(
            dsrc, conn, KEY_TABLE, KEY_ID, KEY_USE, "sig", KEY_ISSUED, 1
        )
    )[0]


async def insert_key(
    dsrc: Source, conn: AsyncConnection, kid: str, iat: str, use: str
) -> int:
    row = {KEY_ID: kid, KEY_ISSUED: iat, KEY_USE: use}
    return await insert(dsrc, conn, KEY_TABLE, row)


async def insert_jwk(
    dsrc: Source, conn: AsyncConnection, encrypted_jwk_set: str
) -> int:
    jwk_set_row = {"id": 1, JWK_VALUE: encrypted_jwk_set}
    return await insert(dsrc, conn, JWK_TABLE, jwk_set_row)


async def update_jwk(
    dsrc: Source, conn: AsyncConnection, encrypted_jwk_set: str
) -> int:
    return await update_column_by_unique(
        dsrc, conn, JWK_TABLE, JWK_VALUE, encrypted_jwk_set, "id", 1
    )


async def get_jwk(dsrc: Source, conn: AsyncConnection) -> str:
    row_dict = await retrieve_by_id(dsrc, conn, JWK_TABLE, 1)
    if row_dict is None:
        raise DataError(message=f"JWK Set missing.", key="missing_jwks")
    return JWKSRow.parse_obj(row_dict).encrypted_value
