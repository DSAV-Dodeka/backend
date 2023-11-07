from sqlalchemy.ext.asyncio import AsyncConnection

from schema.model import (
    JWK_VALUE,
    KEY_ID,
    KEY_ISSUED,
    KEY_USE,
    KEY_TABLE,
    JWK_TABLE,
)
from store.db import (
    LiteralDict,
    retrieve_by_id,
    get_largest_where,
    update_column_by_unique,
    insert,
)
from apiserver.lib.model.entities import JWKSRow, StoredKeyKID
from store.error import DataError, NoDataError

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
    first_key = StoredKeyKID.model_validate(results[0])
    second_key = StoredKeyKID.model_validate(results[1])

    return first_key.kid, second_key.kid


async def get_newest_pem(conn: AsyncConnection) -> str:
    largest = await get_largest_where(
        conn, KEY_TABLE, {KEY_ID}, KEY_USE, "sig", KEY_ISSUED, 1
    )
    if len(largest) == 0:
        raise NoDataError(
            message="There is no most recent signing key!",
            key="missing_symmetric_keys",
        )

    signing_key = StoredKeyKID.model_validate(largest[0])

    return signing_key.kid


async def insert_key(conn: AsyncConnection, kid: str, iat: int, use: str) -> int:
    row: LiteralDict = {KEY_ID: kid, KEY_ISSUED: iat, KEY_USE: use}
    return await insert(conn, KEY_TABLE, row)


async def insert_jwk(conn: AsyncConnection, encrypted_jwk_set: str) -> int:
    jwk_set_row: LiteralDict = {"id": 1, JWK_VALUE: encrypted_jwk_set}
    return await insert(conn, JWK_TABLE, jwk_set_row)


async def update_jwk(conn: AsyncConnection, encrypted_jwk_set: str) -> None:
    cnt = await update_column_by_unique(
        conn, JWK_TABLE, JWK_VALUE, encrypted_jwk_set, "id", 1
    )
    if cnt == 0:
        raise NoDataError(
            message="JWK Set missing when trying update.", key="missing_jwks_on_update"
        )


async def get_jwk(conn: AsyncConnection) -> str:
    row_dict = await retrieve_by_id(conn, JWK_TABLE, 1)
    if row_dict is None:
        raise DataError(message="JWK Set missing.", key="missing_jwks")
    return JWKSRow.model_validate(row_dict).encrypted_value
