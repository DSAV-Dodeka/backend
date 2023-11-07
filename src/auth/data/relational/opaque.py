from typing import Any, Optional

from sqlalchemy.ext.asyncio import AsyncConnection

from store.error import DataError
from schema.model import OPAQUE_SETUP_TABLE
from store.db import lit_model, retrieve_by_id, insert
from auth.data.relational.entities import OpaqueSetup

__all__ = ["get_setup", "insert_opaque_row"]


async def _get_opaque_row(
    conn: AsyncConnection, id_int: int
) -> Optional[dict[str, Any]]:
    opaque_row = await retrieve_by_id(conn, OPAQUE_SETUP_TABLE, id_int)

    return opaque_row


async def _get_opaque_setup(conn: AsyncConnection) -> OpaqueSetup:
    # TODO set id in config
    id_int = 0
    opaque_row = await _get_opaque_row(conn, id_int)
    if opaque_row is None:
        raise DataError(
            message=f"Opaque setup missing for id {id_int}", key="missing_opaque_setup"
        )
    return OpaqueSetup.model_validate(opaque_row)


async def get_setup(conn: AsyncConnection) -> str:
    return (await _get_opaque_setup(conn)).value


async def insert_opaque_row(conn: AsyncConnection, opaque_setup: OpaqueSetup) -> int:
    return await insert(conn, OPAQUE_SETUP_TABLE, lit_model(opaque_setup))
