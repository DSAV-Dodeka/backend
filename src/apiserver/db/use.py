import contextlib
from typing import Optional, Any, AsyncIterator, Callable

from sqlalchemy import text
from sqlalchemy.engine import CursorResult
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncTransaction, AsyncConnection
from sqlalchemy.sql.elements import TextClause

from apiserver.db.ops import DbOperations, DbError

__all__ = ["PostgresOperations"]


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
    conn: AsyncConnection, query, params: dict
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


def all_rows(res: CursorResult) -> list[dict]:
    rows = res.mappings().all()
    return [dict(row) for row in rows]


def row_cnt(res: CursorResult) -> int:
    return res.rowcount


class PostgresOperations(DbOperations):
    """
    The DatabaseOperations class provides an easily referencable object that can be mocked.
    This circumvents a problem where mocks are ignored as FastAPI changes the function
    references at startup.
    """

    @classmethod
    def begin_conn(cls, engine: AsyncEngine) -> AsyncIterator[AsyncConnection]:
        return engine.begin()

    @classmethod
    async def retrieve_by_id(
        cls, conn: AsyncConnection, table: str, id_int: int
    ) -> Optional[dict]:
        """Ensure `table` is never user-defined."""
        query = text(f"SELECT * FROM {table} WHERE id = :id;")
        res: CursorResult = await conn.execute(query, parameters={"id": id_int})
        return first_or_none(res)

    @classmethod
    async def retrieve_by_unique(
        cls, conn: AsyncConnection, table: str, unique_column: str, value
    ) -> Optional[dict]:
        """Ensure `table` and `unique_column` are never user-defined."""
        query = text(f"SELECT * FROM {table} WHERE {unique_column} = :val;")
        res: CursorResult = await conn.execute(query, parameters={"val": value})
        return first_or_none(res)

    @classmethod
    async def select_some_where(
        cls,
        conn: AsyncConnection,
        table: str,
        sel_col: set[str],
        where_col: str,
        where_value,
    ) -> list[dict]:
        """Ensure `table`, `where_col` and `sel_col` are never user-defined."""
        some = select_set(sel_col)
        query = text(f"SELECT {some} FROM {table} WHERE {where_col} = :val;")
        res = await conn.execute(query, parameters={"val": where_value})
        return all_rows(res)

    @classmethod
    async def select_some_two_where(
        cls,
        conn: AsyncConnection,
        table: str,
        sel_col: set[str],
        where_col1: str,
        where_value1,
        where_col2: str,
        where_value2,
    ) -> list[dict]:
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

    @classmethod
    async def select_where(
        cls, conn: AsyncConnection, table: str, column, value
    ) -> list[dict]:
        """Ensure `table` and `column` are never user-defined."""
        query = text(f"SELECT * FROM {table} WHERE {column} = :val;")
        res = await conn.execute(query, parameters={"val": value})
        return all_rows(res)

    @classmethod
    async def get_largest_where(
        cls,
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
        some = select_set(sel_col)
        query = text(
            f"SELECT {some} FROM {table} where {where_col} = :where_val ORDER BY"
            f" {order_col} DESC LIMIT {num};"
        )
        res: CursorResult = await conn.execute(
            query, parameters={"where_val": where_val}
        )
        return list(res.scalars().all())

    @classmethod
    async def exists_by_unique(
        cls, conn: AsyncConnection, table: str, unique_column: str, value
    ) -> bool:
        """Ensure `unique_column` and `table` are never user-defined."""
        query = text(
            f"SELECT EXISTS (SELECT * FROM {table} WHERE {unique_column} = :val) AS"
            ' "exists";'
        )
        res: CursorResult = await conn.scalar(query, parameters={"val": value})
        return res if res is not None else False

    @classmethod
    async def upsert_by_unique(
        cls, conn: AsyncConnection, table: str, row: dict, unique_column: str
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

    @classmethod
    async def update_column_by_unique(
        cls,
        conn: AsyncConnection,
        table: str,
        set_column: str,
        set_value,
        unique_column: str,
        value,
    ) -> int:
        """Note that while the values are safe from injection, the column names are not.
        """

        query = text(
            f"UPDATE {table} SET {set_column} = :set WHERE {unique_column} = :val;"
        )

        res = await execute_catch_conn(
            conn, query, params={"set": set_value, "val": value}
        )
        return row_cnt(res)

    @classmethod
    async def concat_column_by_unique_returning(
        cls,
        conn: AsyncConnection,
        table: str,
        concat_source_column: str,
        concat_target_column: str,
        concat_value,
        unique_column: str,
        value,
        return_col: str,
    ) -> Any:
        """Note that while the values are safe from injection, the column names are not.
        """

        query = text(
            f"UPDATE {table} SET {concat_target_column} = {concat_source_column} ||"
            f" :add WHERE {unique_column} = :val RETURNING ({return_col});"
        )

        res = await execute_catch_conn(
            conn, query, params={"add": concat_value, "val": value}
        )
        return res.scalar()

    @classmethod
    async def insert(cls, conn: AsyncConnection, table: str, row: dict) -> int:
        """Note that while the values are safe from injection, the column names are not. Ensure the row dict
        is validated using the model and not just passed directly by the user."""

        row_keys, row_keys_vars, _ = _row_keys_vars_set(row)
        query = text(f"INSERT INTO {table} ({row_keys}) VALUES ({row_keys_vars});")

        res: CursorResult = await execute_catch_conn(conn, query, params=row)
        return row_cnt(res)

    @classmethod
    async def insert_return_col(
        cls, conn: AsyncConnection, table: str, row: dict, return_col: str
    ) -> Any:
        """Note that while the values are safe from injection, the column names are not. Ensure the row dict
        is validated using the model and not just passed directly by the user."""
        row_keys, row_keys_vars, _ = _row_keys_vars_set(row)

        query = text(
            f"INSERT INTO {table} ({row_keys}) VALUES ({row_keys_vars}) RETURNING"
            f" ({return_col});"
        )

        return await conn.scalar(query, parameters=row)

    @classmethod
    async def delete_by_id(cls, conn: AsyncConnection, table: str, id_int: int) -> int:
        """Ensure `table` is never user-defined."""
        query = text(f"DELETE FROM {table} WHERE id = :id;")
        res: CursorResult = await conn.execute(query, parameters={"id": id_int})
        return row_cnt(res)

    @classmethod
    async def delete_by_column(
        cls, conn: AsyncConnection, table: str, column: str, column_val
    ) -> int:
        """Ensure `table`, `column` and `column_val` are never user-defined."""
        query = text(f"DELETE FROM {table} WHERE {column} = :val;")
        res: CursorResult = await conn.execute(query, parameters={"val": column_val})
        return row_cnt(res)
