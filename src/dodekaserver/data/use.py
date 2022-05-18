from typing import Optional

from dodekaserver.data import Source


async def retrieve_by_id(dsrc: Source, table: str, id_int: int) -> Optional[dict]:
    return await dsrc.gateway.ops.retrieve_by_id(dsrc.gateway.db, table, id_int)


async def retrieve_by_unique(dsrc: Source, table: str, unique_column: str, value) -> Optional[dict]:
    return await dsrc.gateway.ops.retrieve_by_unique(dsrc.gateway.db, table, unique_column, value)


async def upsert_by_id(dsrc: Source, table: str, row: dict):
    return await dsrc.gateway.ops.upsert_by_id(dsrc.gateway.db, table, row)


async def insert_return_id(dsrc: Source, table: str, row: dict) -> int:
    return await dsrc.gateway.ops.insert_return_id(dsrc.gateway.db, table, row)


async def delete_by_id(dsrc: Source, table: str, id_int: int):
    return await dsrc.gateway.ops.delete_by_id(dsrc.gateway.db, table, id_int)


async def delete_by_column(dsrc: Source, table: str, column: str, column_val):
    return await dsrc.gateway.ops.delete_by_column(dsrc.gateway.db, table, column, column_val)


async def delete_insert_return_id_transaction(dsrc: Source, table: str, id_int_delete: int, new_row: dict) -> int:
    return await dsrc.gateway.ops.delete_insert_return_id_transaction(dsrc.gateway.db, table, id_int_delete, new_row)

