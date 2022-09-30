from typing import Optional

from sqlalchemy.ext.asyncio import AsyncConnection

from apiserver.data.use import retrieve_by_id, upsert_by_id
from apiserver.define.entities import OpaqueSetup
from apiserver.data.source import Source, DataError
from apiserver.db import OPAQUE_SETUP_TABLE

__all__ = ['get_setup', 'upsert_opaque_row']


async def _get_opaque_row(dsrc: Source, conn: AsyncConnection, id_int: int) -> Optional[dict]:
    opaque_row = await retrieve_by_id(dsrc, conn, OPAQUE_SETUP_TABLE, id_int)

    return opaque_row


async def _get_opaque_setup(dsrc: Source, conn: AsyncConnection) -> OpaqueSetup:
    # TODO set id in config
    id_int = 0
    opaque_row = await _get_opaque_row(dsrc, conn, id_int)
    if opaque_row is None:
        # new_setup = new_opaque_setup(0)
        # await upsert_opaque_row(dsrc, new_setup.dict())
        # opaque_row = await _get_opaque_row(dsrc, id_int)
        raise DataError(message=f"Opaque setup missing for id {id_int}", key="missing_opaque_setup")
    return OpaqueSetup.parse_obj(opaque_row)


async def get_setup(dsrc: Source, conn: AsyncConnection) -> str:
    return (await _get_opaque_setup(dsrc, conn)).value


async def upsert_opaque_row(dsrc: Source, opaque_setup: OpaqueSetup):
    return await upsert_by_id(dsrc, OPAQUE_SETUP_TABLE, opaque_setup.dict())
