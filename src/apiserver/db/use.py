import asyncio
from typing import Optional, Any

from asyncpg.exceptions import UniqueViolationError
from sqlalchemy import lambda_stmt, text
from sqlalchemy.engine import CursorResult, Row
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncTransaction, AsyncConnection
from sqlalchemy.exc import IntegrityError

from apiserver.db.ops import DbOperations, DbError

__all__ = ['PostgresOperations']


def _row_keys_vars_set(row: dict):
    row_keys = []
    row_keys_vars = []
    row_keys_set = []
    for key in row.keys():
        row_keys.append(key)
        row_keys_vars.append(f':{key}')
        row_keys_set.append(f'{key} = :{key}')
    row_keys = ', '.join(row_keys)
    row_keys_vars = ', '.join(row_keys_vars)
    row_keys_set = ', '.join(row_keys_set)
    return row_keys, row_keys_vars, row_keys_set


async def execute_catch_conn(conn: AsyncConnection, query, params: dict) -> CursorResult:
    try:
        result = await conn.execute(query, parameters=params)
    except IntegrityError as e:
        raise DbError("Database relational integrity violation", str(e), "integrity_violation")

    return result


def first_or_none(res: CursorResult) -> Optional[dict]:
    row = res.first()
    return dict(row) if row is not None else None


def all_rows(res: CursorResult) -> list[dict]:
    rows = res.all()
    return [dict(row) for row in rows]


class PostgresOperations(DbOperations):
    """
    The DatabaseOperations class provides an easily referencable object that can be mocked.
    This circumvents a problem where mocks are ignored as FastAPI changes the function
    references at startup.
    """

    @classmethod
    def begin_conn(cls, engine: AsyncEngine) -> AsyncTransaction:
        return engine.begin()

    @classmethod
    async def retrieve_by_id(cls, conn: AsyncConnection, table: str, id_int: int) -> Optional[dict]:
        query = text(f"SELECT * FROM {table} WHERE id = :id;")
        res: CursorResult = await conn.execute(query, parameters={"id": id_int})
        return first_or_none(res)

    @classmethod
    async def retrieve_by_unique(cls, conn: AsyncConnection, table: str, unique_column: str, value) -> Optional[dict]:
        query = text(f"SELECT * FROM {table} WHERE {unique_column} = :val;")
        res: CursorResult = await conn.execute(query, parameters={"val": value})
        return first_or_none(res)

    @classmethod
    async def fetch_column_by_unique(cls, conn: AsyncConnection, table: str, fetch_column: str, unique_column: str,
                                     value) -> Optional[Any]:
        """ Ensure `unique_column` and `table` are never user-defined. """
        query = text(f"SELECT {fetch_column} FROM {table} WHERE {unique_column} = :val;")
        return await conn.scalar(query, parameters={"val": value})

    @classmethod
    async def select_where(cls, conn: AsyncConnection, table: str, column, value) -> list[dict]:
        """ Ensure `table` is never user-defined. """
        query = text(f"SELECT * FROM {table} WHERE {column} = :val;")
        res = await conn.execute(query, parameters={"val": value})
        return all_rows(res)

    @classmethod
    async def get_largest_where(cls, conn: AsyncConnection, table: str, res_col: str, where_col: str, where_val,
                                order_col: str, num: int) -> list[Any]:
        query = text(f"SELECT {res_col} FROM {table} where {where_col} = :where_val ORDER BY {order_col} DESC LIMIT "
                     f"{num};")
        res: CursorResult = await conn.execute(query, parameters={"where_val": where_val})
        return res.scalars().all()

    @classmethod
    async def exists_by_unique(cls, conn: AsyncConnection, table: str, unique_column: str, value) -> bool:
        """ Ensure `unique_column` and `table` are never user-defined. """
        query = text(f"SELECT EXISTS (SELECT * FROM {table} WHERE {unique_column} = :val) AS \"exists\";")
        res: CursorResult = await conn.scalar(query, parameters={"val": value})
        return res if res is not None else False

    @classmethod
    async def upsert_by_unique(cls, conn: AsyncConnection, table: str, row: dict, unique_column: str) -> int:
        """ Note that while the values are safe from injection, the column names are not. Ensure the row dict
        is validated using the model and not just passed directly by the user. This does not allow changing
         any columns that have unique constraints, those must remain unaltered. """
        row_keys, row_keys_vars, row_keys_set = _row_keys_vars_set(row)

        query = text(f"INSERT INTO {table} ({row_keys}) VALUES ({row_keys_vars}) ON CONFLICT ({unique_column}) DO "
                     f"UPDATE SET {row_keys_set};")

        res = await execute_catch_conn(conn, query, params=row)
        return res.rowcount

    @classmethod
    async def update_column_by_unique(cls, conn: AsyncConnection, table: str, set_column: str, set_value,
                                      unique_column: str, value) -> int:
        """ Note that while the values are safe from injection, the column names are not. """

        query = text(f"UPDATE {table} SET {set_column} = :set WHERE {unique_column} = :val;")

        res = await execute_catch_conn(conn, query, params={"set": set_value, "val": value})
        return res.rowcount

    @classmethod
    async def insert(cls, conn: AsyncConnection, table: str, row: dict) -> int:
        """ Note that while the values are safe from injection, the column names are not. Ensure the row dict
        is validated using the model and not just passed directly by the user. """

        row_keys, row_keys_vars, _ = _row_keys_vars_set(row)
        query = text(f"INSERT INTO {table} ({row_keys}) VALUES ({row_keys_vars});")

        res: CursorResult = await conn.execute(query, parameters=row)
        return res.rowcount

    @classmethod
    async def insert_return_col(cls, conn: AsyncConnection, table: str, row: dict, return_col: str) -> Any:
        """ Note that while the values are safe from injection, the column names are not. Ensure the row dict
        is validated using the model and not just passed directly by the user. """
        row_keys, row_keys_vars, _ = _row_keys_vars_set(row)

        query = text(f"INSERT INTO {table} ({row_keys}) VALUES ({row_keys_vars}) RETURNING ({return_col});")

        return await conn.scalar(query, parameters=row)

    @classmethod
    async def delete_by_id(cls, conn: AsyncConnection, table: str, id_int: int) -> int:
        query = text(f"DELETE FROM {table} WHERE id = :id;")
        res: CursorResult = await conn.execute(query, parameters={"id": id_int})
        return res.rowcount

    @classmethod
    async def delete_by_column(cls, conn: AsyncConnection, table: str, column: str, column_val) -> int:
        query = text(f"DELETE FROM {table} WHERE {column} = :{column};")
        res: CursorResult = await conn.execute(query, parameters={column: column_val})
        return res.rowcount

