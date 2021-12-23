from opaquepy.lib import generate_keys

from dodekaserver.data.source import Source
from dodekaserver.db import KEY_TABLE
from dodekaserver.db.model import PUBLIC_KEY_COLUMN, PRIVATE_KEY_COLUMN


__all__ = ['get_public_key', 'get_private_key', 'upsert_key_row']


async def _get_key_row(dsrc: Source, id_int: int) -> dict:
    key_row = await dsrc.ops.retrieve_by_id(dsrc.db, KEY_TABLE, id_int)
    if key_row is None and id_int == 0:
        private, public = generate_keys()
        new_key_row = create_key_row(0, public, private)
        await upsert_key_row(dsrc, new_key_row)
        key_row = await dsrc.ops.retrieve_by_id(dsrc.db, KEY_TABLE, 0)
    return key_row


async def get_public_key(dsrc: Source, id_int: int) -> str:
    key_row = await _get_key_row(dsrc, id_int)
    return key_row.get(PUBLIC_KEY_COLUMN)


async def get_private_key(dsrc: Source, id_int: int) -> str:
    key_row = await _get_key_row(dsrc, id_int)
    return key_row.get(PRIVATE_KEY_COLUMN)


async def upsert_key_row(dsrc: Source, key_row: dict):
    return await dsrc.ops.upsert_by_id(dsrc.db, KEY_TABLE, key_row)


def create_key_row(id_int: int, public: str, private: str):
    return {
        "id": id_int,
        PUBLIC_KEY_COLUMN: public,
        PRIVATE_KEY_COLUMN: private
    }
