from typing import Optional

from apiserver.data.use import retrieve_by_id, upsert_by_id
from apiserver.define.entities import OpaqueKey, TokenKey, SymmetricKey
from apiserver.data.source import Source, DataError
from apiserver.db import KEY_TABLE
from apiserver.auth.key_util import new_ed448_keypair, new_curve25519_keypair, new_symmetric_key

__all__ = ['get_opaque_public', 'get_opaque_private', 'get_token_private', 'get_token_public', 'upsert_key_row']


async def _get_key_row(dsrc: Source, id_int: int) -> Optional[dict]:
    key_row = await retrieve_by_id(dsrc, KEY_TABLE, id_int)

    return key_row


async def _get_opaque_key(dsrc: Source) -> OpaqueKey:
    # TODO set id in config
    id_int = 0
    key_row = await _get_key_row(dsrc, id_int)
    if key_row is None:
        # new_key = new_curve25519_keypair(id_int)
        # await upsert_key_row(dsrc, new_key.dict())
        # key_row = await dsrc.ops.retrieve_by_id(dsrc.db, KEY_TABLE, id_int)
        raise DataError(message=f"Key missing for id {id_int}", key="missing_key")
    return OpaqueKey.parse_obj(key_row)


async def get_opaque_private(dsrc: Source) -> str:
    return (await _get_opaque_key(dsrc)).private


async def get_opaque_public(dsrc: Source) -> str:
    return (await _get_opaque_key(dsrc)).public


async def _get_token_key(dsrc: Source) -> TokenKey:
    # TODO set id in config
    id_int = 1
    key_row = await _get_key_row(dsrc, id_int)
    if key_row is None:
        # new_key = new_ed448_keypair(1)
        # await upsert_key_row(dsrc, new_key.dict())
        # key_row = await dsrc.ops.retrieve_by_id(dsrc.db, KEY_TABLE, 1)
        raise DataError(message=f"Key missing for id {id_int}", key="missing_key")
    return TokenKey.parse_obj(key_row)


async def _get_symmetric_key(dsrc: Source):
    # TODO set id in config
    id_int = 2
    key_row = await _get_key_row(dsrc, id_int)
    if key_row is None:
        # new_key = new_symmetric_key(id_int)
        # await upsert_key_row(dsrc, new_key.dict())
        # key_row = await dsrc.ops.retrieve_by_id(dsrc.db, KEY_TABLE, 2)
        raise DataError(message=f"Key missing for id {id_int}", key="missing_key")
    return SymmetricKey.parse_obj(key_row)


async def get_token_private(dsrc: Source) -> str:
    return (await _get_token_key(dsrc)).private


async def get_token_public(dsrc: Source) -> str:
    return (await _get_token_key(dsrc)).public


async def get_refresh_symmetric(dsrc: Source) -> str:
    return (await _get_symmetric_key(dsrc)).private


async def upsert_key_row(dsrc: Source, key_row: dict):
    return await upsert_by_id(dsrc, KEY_TABLE, key_row)
