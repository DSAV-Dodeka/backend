from typing import Optional

from dodekaserver.data.entities import OpaqueKey, TokenKey, SymmetricKey
from dodekaserver.data.source import Source
from dodekaserver.db import KEY_TABLE
from dodekaserver.auth.key_util import new_ed448_keypair, new_curve25519_keypair, new_symmetric_key

__all__ = ['get_opaque_public', 'get_opaque_private', 'get_token_private', 'get_token_public', 'upsert_key_row']


async def _get_key_row(dsrc: Source, id_int: int) -> Optional[dict]:
    key_row = await dsrc.ops.retrieve_by_id(dsrc.db, KEY_TABLE, id_int)

    return key_row


async def _get_opaque_key(dsrc: Source) -> OpaqueKey:
    # TODO set id in config
    key_row = await _get_key_row(dsrc, 0)
    if key_row is None:
        new_key = new_curve25519_keypair(0)

        await upsert_key_row(dsrc, new_key.dict())
        key_row = await dsrc.ops.retrieve_by_id(dsrc.db, KEY_TABLE, 0)
    return OpaqueKey.parse_obj(key_row)


async def get_opaque_private(dsrc: Source) -> str:
    return (await _get_opaque_key(dsrc)).private


async def get_opaque_public(dsrc: Source) -> str:
    return (await _get_opaque_key(dsrc)).public


async def _get_token_key(dsrc: Source):
    # TODO set id in config
    key_row = await _get_key_row(dsrc, 1)
    if key_row is None:
        new_key = new_ed448_keypair(1)
        await upsert_key_row(dsrc, new_key.dict())
        key_row = await dsrc.ops.retrieve_by_id(dsrc.db, KEY_TABLE, 1)
    return TokenKey.parse_obj(key_row)


async def _get_symmetric_key(dsrc: Source):
    # TODO set id in config
    key_row = await _get_key_row(dsrc, 2)
    if key_row is None:
        new_key = new_symmetric_key(2)
        await upsert_key_row(dsrc, new_key.dict())
        key_row = await dsrc.ops.retrieve_by_id(dsrc.db, KEY_TABLE, 2)
    return SymmetricKey.parse_obj(key_row)


async def get_token_private(dsrc: Source) -> str:
    return (await _get_token_key(dsrc)).private


async def get_token_public(dsrc: Source) -> str:
    return (await _get_token_key(dsrc)).public


async def get_refresh_symmetric(dsrc: Source) -> str:
    return (await _get_symmetric_key(dsrc)).private


async def upsert_key_row(dsrc: Source, key_row: dict):
    return await dsrc.ops.upsert_by_id(dsrc.db, KEY_TABLE, key_row)
