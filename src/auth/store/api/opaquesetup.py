# from typing import Optional
#
# from sqlalchemy.ext.asyncio import AsyncConnection
#
# from apiserver.data.source import DataError
# from apiserver.data.db.ops import retrieve_by_id, insert
# from apiserver.data.db.model import OPAQUE_SETUP_TABLE
# from apiserver.lib.model.entities import OpaqueSetup
#
# __all__ = ["get_setup", "insert_opaque_row"]
#
#
# async def _get_opaque_row(conn: AsyncConnection, id_int: int) -> Optional[dict]:
#     opaque_row = await retrieve_by_id(conn, OPAQUE_SETUP_TABLE, id_int)
#
#     return opaque_row
#
#
# async def _get_opaque_setup(conn: AsyncConnection) -> OpaqueSetup:
#     # TODO set id in config
#     id_int = 0
#     opaque_row = await _get_opaque_row(conn, id_int)
#     if opaque_row is None:
#         # new_setup = new_opaque_setup(0)
#         # await upsert_opaque_row(dsrc, new_setup.model_dump())
#         # opaque_row = await _get_opaque_row(dsrc, id_int)
#         raise DataError(
#             message=f"Opaque setup missing for id {id_int}", key="missing_opaque_setup"
#         )
#     return OpaqueSetup.model_validate(opaque_row)
#
#
# async def get_setup(conn: AsyncConnection) -> str:
#     return (await _get_opaque_setup(conn)).value
#
#
# async def insert_opaque_row(conn: AsyncConnection, opaque_setup: OpaqueSetup):
#     return await insert(conn, OPAQUE_SETUP_TABLE, opaque_setup.model_dump())
