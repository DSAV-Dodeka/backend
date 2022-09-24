from typing import Optional

from sqlalchemy.ext.asyncio import AsyncConnection

from apiserver.data import Source, DataError


def db_is_init(dsrc: Source):
    if dsrc.gateway.db is None:
        raise DataError("Database not initialized!", "no_db_init")
    else:
        return dsrc.gateway.db


def eng_is_init(dsrc: Source):
    if dsrc.gateway.engine is None:
        raise DataError("Database not initialized!", "no_db_init")
    else:
        return dsrc.gateway.engine


def get_conn(dsrc: Source):
    return dsrc.gateway.ops.begin_conn(eng_is_init(dsrc))


async def retrieve_by_id(dsrc: Source, conn: AsyncConnection, table: str, id_int: int) -> Optional[dict]:
    return await dsrc.gateway.ops.retrieve_by_id(conn, table, id_int)


async def retrieve_by_unique(dsrc: Source, table: str, unique_column: str, value) -> Optional[dict]:
    return await dsrc.gateway.ops.retrieve_by_unique(db_is_init(dsrc), table, unique_column, value)


async def select_where(dsrc: Source, conn: AsyncConnection, table: str, column: str, value) -> list[dict]:
    return await dsrc.gateway.ops.select_where(conn, table, column, value)


async def retrieve_table(dsrc: Source, table: str) -> list[dict]:
    return await dsrc.gateway.ops.retrieve_table(db_is_init(dsrc), table)


async def exists_by_unique(dsrc: Source, table: str, unique_column: str, value) -> bool:
    return await dsrc.gateway.ops.exists_by_unique(db_is_init(dsrc), table, unique_column, value)


async def upsert_by_id(dsrc: Source, table: str, row: dict):
    return await dsrc.gateway.ops.upsert_by_id(db_is_init(dsrc), table, row)


async def update_column_by_unique(dsrc: Source, conn: AsyncConnection, table: str, set_column: str, set_value,
                                  unique_column: str, value):
    return await dsrc.gateway.ops.update_column_by_unique(conn, table, set_column, set_value, unique_column, value)


async def insert(dsrc: Source, table: str, row: dict):
    return await dsrc.gateway.ops.insert(db_is_init(dsrc), table, row)


async def insert_return_id(dsrc: Source, table: str, row: dict) -> int:
    return await dsrc.gateway.ops.insert_return_id(db_is_init(dsrc), table, row)


async def delete_by_id(dsrc: Source, table: str, id_int: int):
    return await dsrc.gateway.ops.delete_by_id(db_is_init(dsrc), table, id_int)


async def delete_by_column(dsrc: Source, table: str, column: str, column_val):
    return await dsrc.gateway.ops.delete_by_column(db_is_init(dsrc), table, column, column_val)


async def delete_insert_return_id_transaction(dsrc: Source, table: str, id_int_delete: int, new_row: dict) -> int:
    return await dsrc.gateway.ops.delete_insert_return_id_transaction(db_is_init(dsrc), table, id_int_delete, new_row)


async def double_insert_transaction(dsrc: Source, first_table: str, first_row: dict, second_table: str,
                                    second_row: dict):
    return await dsrc.gateway.ops.double_insert_transaction(db_is_init(dsrc), first_table, first_row, second_table,
                                                            second_row)
