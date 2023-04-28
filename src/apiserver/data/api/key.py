from sqlalchemy.ext.asyncio import AsyncConnection

from apiserver.data.db.model import (
    JWK_VALUE,
    KEY_ID,
    KEY_ISSUED,
    KEY_USE,
    KEY_TABLE,
    JWK_TABLE,
)
from apiserver.data.db.ops import (
    retrieve_by_id,
    get_largest_where,
    update_column_by_unique,
    insert,
)
from apiserver.lib.model.entities import JWKSRow
from apiserver.data.source import DataError


MINIMUM_KEYS = 2


async def get_newest_symmetric(conn: AsyncConnection) -> tuple[str, str]:
    results = await get_largest_where(
        conn, KEY_TABLE, {KEY_ID}, KEY_USE, "enc", KEY_ISSUED, 2
    )
    if len(results) < MINIMUM_KEYS:
        raise DataError(
            message="There should be at least two symmetric keys.",
            key="missing_symmetric_keys",
        )
    return results[0], results[1]


async def get_newest_pem(conn: AsyncConnection) -> str:
    return (
        await get_largest_where(
            conn, KEY_TABLE, {KEY_ID}, KEY_USE, "sig", KEY_ISSUED, 1
        )
    )[0]


async def insert_key(conn: AsyncConnection, kid: str, iat: int, use: str) -> int:
    row = {KEY_ID: kid, KEY_ISSUED: iat, KEY_USE: use}
    return await insert(conn, KEY_TABLE, row)


async def insert_jwk(conn: AsyncConnection, encrypted_jwk_set: str) -> int:
    jwk_set_row = {"id": 1, JWK_VALUE: encrypted_jwk_set}
    return await insert(conn, JWK_TABLE, jwk_set_row)


async def update_jwk(conn: AsyncConnection, encrypted_jwk_set: str) -> int:
    return await update_column_by_unique(
        conn, JWK_TABLE, JWK_VALUE, encrypted_jwk_set, "id", 1
    )


async def get_jwk(conn: AsyncConnection) -> str:
    row_dict = await retrieve_by_id(conn, JWK_TABLE, 1)
    if row_dict is None:
        raise DataError(message="JWK Set missing.", key="missing_jwks")
    return JWKSRow.parse_obj(row_dict).encrypted_value
