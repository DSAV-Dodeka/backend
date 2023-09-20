from typing import Optional, Any, TypeVar, LiteralString

from pydantic import BaseModel
from sqlalchemy import CursorResult, text, RowMapping
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncConnection


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
    conn: AsyncConnection, table: LiteralString, id_int: int
) -> Optional[dict]:
    """Ensure `table` is never user-defined."""
    query = text(f"SELECT * FROM {table} WHERE id = :id;")
    res: CursorResult = await conn.execute(query, parameters={"id": id_int})
    return first_or_none(res)


async def retrieve_by_unique(
    conn: AsyncConnection, table: LiteralString, unique_column: LiteralString, value
) -> Optional[dict]:
    """Ensure `table` and `unique_column` are never user-defined."""
    query = text(f"SELECT * FROM {table} WHERE {unique_column} = :val;")
    res: CursorResult = await conn.execute(query, parameters={"val": value})
    return first_or_none(res)


async def select_some_where(
    conn: AsyncConnection,
    table: LiteralString,
    sel_col: set[LiteralString],
    where_col: LiteralString,
    where_value,
) -> list[RowMapping]:
    """Ensure `table`, `where_col` and `sel_col` are never user-defined."""
    some = select_set(sel_col)
    query = text(f"SELECT {some} FROM {table} WHERE {where_col} = :val;")
    res = await conn.execute(query, parameters={"val": where_value})
    return all_rows(res)


async def select_some_two_where(
    conn: AsyncConnection,
    table: LiteralString,
    sel_col: set[LiteralString],
    where_col1: LiteralString,
    where_value1,
    where_col2: LiteralString,
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
    sel_col: set[LiteralString],
    table_1: LiteralString,
    table_2: LiteralString,
    join_col_1: LiteralString,
    join_col_2: LiteralString,
    where_col: LiteralString,
    value,
) -> list[RowMapping]:
    """Ensure columns and tables are never user-defined. If some select column exists in both tables, they must be
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
    table: LiteralString,
    sel_col: set[LiteralString],
    where_col: LiteralString,
    where_val,
    order_col: LiteralString,
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
    conn: AsyncConnection, table: LiteralString, unique_column: LiteralString, value
) -> bool:
    """Ensure `unique_column` and `table` are never user-defined."""
    query = text(
        f"SELECT EXISTS (SELECT * FROM {table} WHERE {unique_column} = :val) AS"
        ' "exists";'
    )
    res: CursorResult = await conn.scalar(query, parameters={"val": value})
    return res if res is not None else False


async def upsert_by_unique(
    conn: AsyncConnection, table: LiteralString, row: dict, unique_column: LiteralString
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
    table: LiteralString,
    set_column: LiteralString,
    set_value,
    unique_column: LiteralString,
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
    table: LiteralString,
    concat_source_column: LiteralString,
    concat_target_column: LiteralString,
    concat_value,
    unique_column: LiteralString,
    value,
    return_col: LiteralString,
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


async def insert(conn: AsyncConnection, table: LiteralString, row: dict) -> int:
    """Note that while the values are safe from injection, the column names are not. Ensure the row dict
    is validated using the model and not just passed directly by the user."""

    row_keys, row_keys_vars, _ = _row_keys_vars_set(row)
    query = text(f"INSERT INTO {table} ({row_keys}) VALUES ({row_keys_vars});")

    res: CursorResult = await execute_catch_conn(conn, query, params=row)
    return row_cnt(res)


async def insert_return_col(
    conn: AsyncConnection, table: LiteralString, row: dict, return_col: str
) -> Any:
    """Note that while the values are safe from injection, the column names are not. Ensure the row dict
    is validated using the model and not just passed directly by the user."""
    row_keys, row_keys_vars, _ = _row_keys_vars_set(row)

    query = text(
        f"INSERT INTO {table} ({row_keys}) VALUES ({row_keys_vars}) RETURNING"
        f" ({return_col});"
    )

    return await conn.scalar(query, parameters=row)


async def delete_by_id(conn: AsyncConnection, table: LiteralString, id_int: int) -> int:
    """Ensure `table` is never user-defined."""
    query = text(f"DELETE FROM {table} WHERE id = :id;")
    res: CursorResult = await conn.execute(query, parameters={"id": id_int})
    return row_cnt(res)


async def delete_by_column(
    conn: AsyncConnection, table: LiteralString, column: LiteralString, column_val
) -> int:
    """Ensure `table` and `column` are never user-defined."""
    query = text(f"DELETE FROM {table} WHERE {column} = :val;")
    res: CursorResult = await conn.execute(query, parameters={"val": column_val})
    return row_cnt(res)


async def insert_many(
    conn: AsyncConnection, table: LiteralString, row_list: list[dict]
) -> int:
    """The model type must be known beforehand, it cannot be defined by the user! Same goes for table string. The dict
    column values must also be checked!"""
    if len(row_list) == 0:
        raise DbError(
            "List must contain at least one element!", "", "insert_at_least_one_element"
        )
    row_keys, row_keys_vars, _ = _row_keys_vars_set(row_list[0])
    query = text(f"INSERT INTO {table} ({row_keys}) VALUES ({row_keys_vars});")

    res: CursorResult = await execute_catch_conn(conn, query, params=row_list)
    return row_cnt(res)


class DbError(Exception):
    """Exception that represents special internal errors."""

    def __init__(self, err_desc: str, err_internal: str, debug_key: str | None = None):
        self.err_desc = err_desc
        self.err_internal = err_internal
        self.debug_key = debug_key
