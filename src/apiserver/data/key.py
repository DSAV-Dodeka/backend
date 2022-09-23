from typing import Optional

from sqlalchemy.ext.asyncio import AsyncConnection

from apiserver.data.use import retrieve_by_id, upsert_by_id
from apiserver.define.entities import TokenKey, SymmetricKey
from apiserver.data.source import Source, DataError
from apiserver.db import KEY_TABLE
from apiserver.auth.key_util import new_ed448_keypair, new_symmetric_key

__all__ = ['get_token_private', 'get_token_public', 'upsert_key_row']


async def _get_key_row(dsrc: Source, conn: AsyncConnection, id_int: int) -> Optional[dict]:
    key_row = await retrieve_by_id(dsrc, conn, KEY_TABLE, id_int)

    return key_row


async def _get_token_key(dsrc: Source, conn: AsyncConnection) -> TokenKey:
    # TODO set id in config
    id_int = 1
    key_row = await _get_key_row(dsrc, conn, id_int)
    if key_row is None:
        # new_key = new_ed448_keypair(1)
        # await upsert_key_row(dsrc, new_key.dict())
        # key_row = await dsrc.ops.retrieve_by_id(dsrc.db, KEY_TABLE, 1)
        raise DataError(message=f"Key missing for id {id_int}", key="missing_key")
    return TokenKey.parse_obj(key_row)


async def _get_symmetric_key(dsrc: Source, conn: AsyncConnection):
    # TODO set id in config
    id_int = 2
    key_row = await _get_key_row(dsrc, conn, id_int)
    if key_row is None:
        # new_key = new_symmetric_key(id_int)
        # await upsert_key_row(dsrc, new_key.dict())
        # key_row = await dsrc.ops.retrieve_by_id(dsrc.db, KEY_TABLE, 2)
        raise DataError(message=f"Key missing for id {id_int}", key="missing_key")
    return SymmetricKey.parse_obj(key_row)


async def get_token_private(dsrc: Source, conn: AsyncConnection) -> str:
    return (await _get_token_key(dsrc, conn)).private


async def get_token_public(dsrc: Source, conn: AsyncConnection) -> str:
    return (await _get_token_key(dsrc, conn)).public


async def get_refresh_symmetric(dsrc: Source, conn: AsyncConnection) -> str:
    return (await _get_symmetric_key(dsrc, conn)).private


async def upsert_key_row(dsrc: Source, key_row: dict):
    return await upsert_by_id(dsrc, KEY_TABLE, key_row)
