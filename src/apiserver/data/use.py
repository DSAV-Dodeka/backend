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
    """Ensure `table` is never user-defined."""
    return await dsrc.gateway.ops.retrieve_by_id(conn, table, id_int)


async def retrieve_by_unique(
    dsrc: Source, conn: AsyncConnection, table: str, unique_column: str, value
) -> Optional[dict]:
    """Ensure `table` and `unique_column` are never user-defined."""
    return await dsrc.gateway.ops.retrieve_by_unique(conn, table, unique_column, value)


async def select_some_where(
    dsrc: Source,
    conn: AsyncConnection,
    table: str,
    sel_col: set[str],
    where_col: str,
    where_value,
) -> list[dict]:
    """Ensure `table`, `where_col` and `sel_col` are never user-defined."""
    return await dsrc.gateway.ops.select_some_where(
        conn, table, sel_col, where_col, where_value
    )


async def select_where(
    dsrc: Source, conn: AsyncConnection, table: str, column: str, value
) -> list[dict]:
    """Ensure `table` and `column` are never user-defined."""
    return await dsrc.gateway.ops.select_where(conn, table, column, value)


async def get_largest_where(
    dsrc: Source,
    conn: AsyncConnection,
    table: str,
    sel_col: set[str],
    where_col: str,
    where_val,
    order_col: str,
    num: int,
) -> list[Any]:
    """Ensure `table`, `sel_col`, `where_col`, `order_col` and `num` are never user-defined.
    """
    return await dsrc.gateway.ops.get_largest_where(
        conn, table, sel_col, where_col, where_val, order_col, num
    )


async def exists_by_unique(
    dsrc: Source, conn: AsyncConnection, table: str, unique_column: str, value
) -> bool:
    """Ensure `unique_column` and `table` are never user-defined."""
    return await dsrc.gateway.ops.exists_by_unique(conn, table, unique_column, value)


async def upsert_by_unique(
    dsrc: Source, conn: AsyncConnection, table: str, row: dict, unique_column: str
):
    """Ensure `table`, `unique_column` and the `row` keys are never user-defined."""
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
    """Ensure `table`, `unique_column` and the `set_column` are never user-defined."""
    return await dsrc.gateway.ops.update_column_by_unique(
        conn, table, set_column, set_value, unique_column, value
    )


async def insert(dsrc: Source, conn: AsyncConnection, table: str, row: dict):
    """Ensure `table` and the `row` keys are never user-defined."""
    return await dsrc.gateway.ops.insert(conn, table, row)


async def insert_return_col(
    dsrc: Source, conn: AsyncConnection, table: str, row: dict, return_col: str
) -> Any:
    """Ensure `table`, `return_col`, and the `row` keys are never user-defined."""
    return await dsrc.gateway.ops.insert_return_col(conn, table, row, return_col)


async def delete_by_id(dsrc: Source, conn: AsyncConnection, table: str, id_int: int):
    """Ensure `table` is never user-defined."""
    return await dsrc.gateway.ops.delete_by_id(conn, table, id_int)


async def delete_by_column(
    dsrc: Source, conn: AsyncConnection, table: str, column: str, column_val
) -> int:
    """Ensure `table`, `column` and `column_val` are never user-defined."""
    return await dsrc.gateway.ops.delete_by_column(conn, table, column, column_val)
