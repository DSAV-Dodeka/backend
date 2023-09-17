from typing import Optional, Any, TypeVar

from pydantic import BaseModel
from sqlalchemy import CursorResult, text, RowMapping
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncConnection

# Model type
# Ensure the type of model is never user-defined, as attribute (column) names are used as strings
#
M = TypeVar("M", bound=BaseModel)


def _row_keys_vars_set(row: dict):
    row_keys = []
    row_keys_vars = []
    row_keys_set = []
    for key in row.keys():
        row_keys.append(key)
        row_keys_vars.append(f":{key}")
        row_keys_set.append(f"{key} = :{key}")
    row_keys = ", ".join(row_keys)
    row_keys_vars = ", ".join(row_keys_vars)
    row_keys_set = ", ".join(row_keys_set)
    return row_keys, row_keys_vars, row_keys_set


def select_set(columns: set[str]):
    return ", ".join(columns)


async def execute_catch_conn(
    conn: AsyncConnection, query, params: dict | list[dict]
) -> CursorResult:
    try:
        result = await conn.execute(query, parameters=params)
    except IntegrityError as e:
        raise DbError(
            "Database relational integrity violation", str(e), "integrity_violation"
        )

    return result


def first_or_none(res: CursorResult) -> Optional[dict]:
    row = res.mappings().first()
    return dict(row) if row is not None else None


def all_rows(res: CursorResult) -> list[RowMapping]:
    return list(res.mappings().all())


def row_cnt(res: CursorResult) -> int:
    return res.rowcount


async def retrieve_by_id(
    conn: AsyncConnection, table: str, id_int: int
) -> Optional[dict]:
    """Ensure `table` is never user-defined."""
    query = text(f"SELECT * FROM {table} WHERE id = :id;")
    res: CursorResult = await conn.execute(query, parameters={"id": id_int})
    return first_or_none(res)


async def retrieve_by_unique(
    conn: AsyncConnection, table: str, unique_column: str, value
) -> Optional[dict]:
    """Ensure `table` and `unique_column` are never user-defined."""
    query = text(f"SELECT * FROM {table} WHERE {unique_column} = :val;")
    res: CursorResult = await conn.execute(query, parameters={"val": value})
    return first_or_none(res)


async def select_some_where(
    conn: AsyncConnection,
    table: str,
    sel_col: set[str],
    where_col: str,
    where_value,
) -> list[RowMapping]:
    """Ensure `table`, `where_col` and `sel_col` are never user-defined."""
    some = select_set(sel_col)
    query = text(f"SELECT {some} FROM {table} WHERE {where_col} = :val;")
    res = await conn.execute(query, parameters={"val": where_value})
    return all_rows(res)


async def select_some_two_where(
    conn: AsyncConnection,
    table: str,
    sel_col: set[str],
    where_col1: str,
    where_value1,
    where_col2: str,
    where_value2,
) -> list[RowMapping]:
    """Ensure `table`, `where_col` and `sel_col` are never user-defined."""
    some = select_set(sel_col)
    query = text(
        f"SELECT {some} FROM {table} WHERE {where_col1} = :vala AND {where_col2} ="
        " :valb;"
    )
    res = await conn.execute(
        query, parameters={"vala": where_value1, "valb": where_value2}
    )
    return all_rows(res)


async def select_where(
    conn: AsyncConnection, table: str, column, value
) -> list[RowMapping]:
    """Ensure `table` and `column` are never user-defined."""
    query = text(f"SELECT * FROM {table} WHERE {column} = :val;")
    res = await conn.execute(query, parameters={"val": value})
    return all_rows(res)


async def select_some_join_where(
    conn: AsyncConnection,
    sel_col: set[str],
    table_1: str,
    table_2: str,
    join_col_1: str,
    join_col_2: str,
    where_col: str,
    value,
) -> list[RowMapping]:
    """Ensure columsn and atbles are never user-defined. If some select column exists in both tables, they must be
    namespaced: i.e. <table_1 name>.column, <table_2 name>.column."""
    some = select_set(sel_col)
    query = text(
        f"SELECT {some} FROM {table_1} JOIN {table_2} on {table_1}.{join_col_1} ="
        f" {table_2}.{join_col_2} WHERE {where_col} = :val;"
    )
    res = await conn.execute(query, parameters={"val": value})
    return all_rows(res)


async def get_largest_where(
    conn: AsyncConnection,
    table: str,
    sel_col: set[str],
    where_col: str,
    where_val,
    order_col: str,
    num: int,
    descending: bool = True,
) -> list[RowMapping]:
    """Ensure `table`, `sel_col`, `where_col`, `order_col` and `num` are never user-defined."""
    some = select_set(sel_col)
    desc_str = "DESC" if descending else "ASC"
    query = text(
        f"SELECT {some} FROM {table} where {where_col} = :where_val ORDER BY"
        f" {order_col} {desc_str} LIMIT {num};"
    )
    res: CursorResult = await conn.execute(query, parameters={"where_val": where_val})
    return all_rows(res)


async def exists_by_unique(
    conn: AsyncConnection, table: str, unique_column: str, value
) -> bool:
    """Ensure `unique_column` and `table` are never user-defined."""
    query = text(
        f"SELECT EXISTS (SELECT * FROM {table} WHERE {unique_column} = :val) AS"
        ' "exists";'
    )
    res: CursorResult = await conn.scalar(query, parameters={"val": value})
    return res if res is not None else False


async def upsert_by_unique(
    conn: AsyncConnection, table: str, row: dict, unique_column: str
) -> int:
    """Note that while the values are safe from injection, the column names are not. Ensure the row dict
    is validated using the model and not just passed directly by the user. This does not allow changing
     any columns that have unique constraints, those must remain unaltered."""
    row_keys, row_keys_vars, row_keys_set = _row_keys_vars_set(row)

    query = text(
        f"INSERT INTO {table} ({row_keys}) VALUES ({row_keys_vars}) ON CONFLICT"
        f" ({unique_column}) DO UPDATE SET {row_keys_set};"
    )

    res = await execute_catch_conn(conn, query, params=row)
    return row_cnt(res)


async def update_column_by_unique(
    conn: AsyncConnection,
    table: str,
    set_column: str,
    set_value,
    unique_column: str,
    value,
) -> int:
    """Note that while the values are safe from injection, the column names are not."""

    query = text(
        f"UPDATE {table} SET {set_column} = :set WHERE {unique_column} = :val;"
    )

    res = await execute_catch_conn(conn, query, params={"set": set_value, "val": value})
    return row_cnt(res)


async def concat_column_by_unique_returning(
    conn: AsyncConnection,
    table: str,
    concat_source_column: str,
    concat_target_column: str,
    concat_value,
    unique_column: str,
    value,
    return_col: str,
) -> Any:
    """Note that while the values are safe from injection, the column names are not."""

    query = text(
        f"UPDATE {table} SET {concat_target_column} = {concat_source_column} ||"
        f" :add WHERE {unique_column} = :val RETURNING ({return_col});"
    )

    res = await execute_catch_conn(
        conn, query, params={"add": concat_value, "val": value}
    )
    return res.scalar()


async def insert(conn: AsyncConnection, table: str, row: dict) -> int:
    """Note that while the values are safe from injection, the column names are not. Ensure the row dict
    is validated using the model and not just passed directly by the user."""

    row_keys, row_keys_vars, _ = _row_keys_vars_set(row)
    query = text(f"INSERT INTO {table} ({row_keys}) VALUES ({row_keys_vars});")

    res: CursorResult = await execute_catch_conn(conn, query, params=row)
    return row_cnt(res)


async def insert_return_col(
    conn: AsyncConnection, table: str, row: dict, return_col: str
) -> Any:
    """Note that while the values are safe from injection, the column names are not. Ensure the row dict
    is validated using the model and not just passed directly by the user."""
    row_keys, row_keys_vars, _ = _row_keys_vars_set(row)

    query = text(
        f"INSERT INTO {table} ({row_keys}) VALUES ({row_keys_vars}) RETURNING"
        f" ({return_col});"
    )

    return await conn.scalar(query, parameters=row)


async def delete_by_id(conn: AsyncConnection, table: str, id_int: int) -> int:
    """Ensure `table` is never user-defined."""
    query = text(f"DELETE FROM {table} WHERE id = :id;")
    res: CursorResult = await conn.execute(query, parameters={"id": id_int})
    return row_cnt(res)


async def delete_by_column(
    conn: AsyncConnection, table: str, column: str, column_val
) -> int:
    """Ensure `table`, `column` and `column_val` are never user-defined."""
    query = text(f"DELETE FROM {table} WHERE {column} = :val;")
    res: CursorResult = await conn.execute(query, parameters={"val": column_val})
    return row_cnt(res)


async def insert_many(conn: AsyncConnection, table: str, model_list: list[M]):
    row_list = [r.model_dump() for r in model_list]
    row_keys, row_keys_vars, _ = _row_keys_vars_set(row_list[0])
    query = text(f"INSERT INTO {table} ({row_keys}) VALUES ({row_keys_vars});")

    return await execute_catch_conn(conn, query, params=row_list)


class DbError(Exception):
    """Exception that represents special internal errors."""

    def __init__(self, err_desc: str, err_internal: str, debug_key: str | None = None):
        self.err_desc = err_desc
        self.err_internal = err_internal
        self.debug_key = debug_key
