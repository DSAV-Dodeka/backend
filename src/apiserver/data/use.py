from typing import Optional, Any

from sqlalchemy.ext.asyncio import AsyncConnection

from apiserver.data import Source, DataError


def eng_is_init(dsrc: Source):
    if dsrc.gateway.engine is None:
        raise DataError("Database not initialized!", "no_db_init")
    else:
        return dsrc.gateway.engine


def get_conn(dsrc: Source):
    return dsrc.gateway.ops.begin_conn(eng_is_init(dsrc))


async def retrieve_by_id(
    dsrc: Source, conn: AsyncConnection, table: str, id_int: int
) -> Optional[dict]:
    return await dsrc.gateway.ops.retrieve_by_id(conn, table, id_int)


async def retrieve_by_unique(
    dsrc: Source, conn: AsyncConnection, table: str, unique_column: str, value
) -> Optional[dict]:
    return await dsrc.gateway.ops.retrieve_by_unique(conn, table, unique_column, value)


async def fetch_column_by_unique(
    dsrc: Source,
    conn: AsyncConnection,
    table: str,
    fetch_column: str,
    unique_column: str,
    value,
) -> Optional[Any]:
    return await dsrc.gateway.ops.fetch_column_by_unique(
        conn, table, fetch_column, unique_column, value
    )


async def select_where(
    dsrc: Source, conn: AsyncConnection, table: str, column: str, value
) -> list[dict]:
    return await dsrc.gateway.ops.select_where(conn, table, column, value)


async def get_largest_where(
    dsrc: Source,
    conn: AsyncConnection,
    table: str,
    res_col: str,
    where_col: str,
    where_val,
    order_col: str,
    num: int,
) -> list[Any]:
    return await dsrc.gateway.ops.get_largest_where(
        conn, table, res_col, where_col, where_val, order_col, num
    )


async def exists_by_unique(
    dsrc: Source, conn: AsyncConnection, table: str, unique_column: str, value
) -> bool:
    return await dsrc.gateway.ops.exists_by_unique(conn, table, unique_column, value)


async def upsert_by_unique(
    dsrc: Source, conn: AsyncConnection, table: str, row: dict, unique_column: str
):
    return await dsrc.gateway.ops.upsert_by_unique(conn, table, row, unique_column)


async def update_column_by_unique(
    dsrc: Source,
    conn: AsyncConnection,
    table: str,
    set_column: str,
    set_value,
    unique_column: str,
    value,
) -> int:
    """Note that while the values are safe from injection, the column names are not."""
    return await dsrc.gateway.ops.update_column_by_unique(
        conn, table, set_column, set_value, unique_column, value
    )


async def insert(dsrc: Source, conn: AsyncConnection, table: str, row: dict):
    return await dsrc.gateway.ops.insert(conn, table, row)


async def insert_return_col(
    dsrc: Source, conn: AsyncConnection, table: str, row: dict, return_col: str
) -> Any:
    return await dsrc.gateway.ops.insert_return_col(conn, table, row, return_col)


async def delete_by_id(dsrc: Source, conn: AsyncConnection, table: str, id_int: int):
    return await dsrc.gateway.ops.delete_by_id(conn, table, id_int)


async def delete_by_column(
    dsrc: Source, conn: AsyncConnection, table: str, column: str, column_val
):
    return await dsrc.gateway.ops.delete_by_column(conn, table, column, column_val)
