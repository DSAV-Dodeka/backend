import asyncio
from typing import Optional, Any

from databases import Database
from asyncpg.exceptions import UniqueViolationError
from sqlalchemy import lambda_stmt, text
from sqlalchemy.engine import CursorResult, Row
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncTransaction, AsyncConnection
from sqlalchemy.exc import IntegrityError

from apiserver.db.ops import DbOperations, DbError

__all__ = ['PostgresOperations', 'execute_queries_unsafe']


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


async def execute_queries_unsafe(db: Database, queries: list[str]):
    """ These queries are executed as full query text strings in parallel, which are vulnerable to SQL Injection.
     Do NOT use with user input. """
    executions = [db.execute(query) for query in queries]
    return await asyncio.gather(*executions)


async def execute_catch(db: Database, query, values):
    try:
        result = await db.execute(query=query, values=values)
    except UniqueViolationError as e:
        raise DbError("Key already exists", str(e), "unique_violation")

    return result


async def execute_catch_conn(conn: AsyncConnection, query, params: dict) -> CursorResult:
    try:
        result = await conn.execute(query, parameters=params)
    except IntegrityError as e:
        raise DbError("Database relational integrity violation", str(e), "integrity_violation")

    return result


def row_as_dict(row: Row):
    return row._asdict()


def first_or_none(res: CursorResult) -> Optional[dict]:
    row = res.first()
    return row_as_dict(row) if row is not None else None


def all_rows(res: CursorResult) -> list[dict]:
    rows = res.all()
    return [row_as_dict(row) for row in rows]


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
        query = text(f"SELECT * FROM {table} WHERE id = :id")
        res: CursorResult = await conn.execute(query, parameters={"id": id_int})
        return first_or_none(res)

    @classmethod
    async def retrieve_by_unique(cls, db: Database, table: str, unique_column: str, value) -> Optional[dict]:
        """ Ensure `unique_column` and `table` are never user-defined. """
        query = f"SELECT * FROM {table} WHERE {unique_column} = :val"
        record = await db.fetch_one(query, values={"val": value})
        return dict(record) if record is not None else None

    @classmethod
    async def fetch_column_by_unique(cls, conn: AsyncConnection, table: str, fetch_column: str, unique_column: str,
                                     value) -> Optional[Any]:
        """ Ensure `unique_column` and `table` are never user-defined. """
        query = text(f"SELECT {fetch_column} FROM {table} WHERE {unique_column} = :val")
        return await conn.scalar(query, parameters={"val": value})

    @classmethod
    async def select_where(cls, conn: AsyncConnection, table: str, column, value) -> list[dict]:
        """ Ensure `table` is never user-defined. """
        query = text(f"SELECT * FROM {table} WHERE {column} = :val")
        res = await conn.execute(query, parameters={"val": value})
        return all_rows(res)

    @classmethod
    async def retrieve_table(cls, db: Database, table: str) -> list[dict]:
        """ Ensure `table` is never user-defined. """
        query = f"SELECT * FROM {table}"
        records = await db.fetch_all(query)
        return [dict(record) for record in records] if records is not None else []

    @classmethod
    async def exists_by_unique(cls, db: Database, table: str, unique_column: str, value) -> bool:
        """ Ensure `unique_column` and `table` are never user-defined. """
        query = f"SELECT EXISTS (SELECT * FROM {table} WHERE {unique_column} = :val) AS \"exists\""
        record = await db.fetch_one(query, values={"val": value})
        return dict(record).get('exists', False) if record is not None else False

    @classmethod
    async def upsert_by_id(cls, db: Database, table: str, row: dict):
        """ Note that while the values are safe from injection, the column names are not. Ensure the row dict
        is validated using the model and not just passed directly by the user. This does not allow changing
         any columns that have unique constraints, those must remain unaltered. """

        row_keys, row_keys_vars, row_keys_set = _row_keys_vars_set(row)

        query = f"INSERT INTO {table} ({row_keys}) VALUES ({row_keys_vars}) ON CONFLICT (id) DO UPDATE SET " \
                f"{row_keys_set};"

        return await execute_catch(db, query=query, values=row)

    @classmethod
    async def update_column_by_unique(cls, conn: AsyncConnection, table: str, set_column: str, set_value,
                                      unique_column: str, value) -> int:
        """ Note that while the values are safe from injection, the column names are not. """

        query = text(f"UPDATE {table} SET {set_column} = :set WHERE {unique_column} = :val;")

        res = await execute_catch_conn(conn, query, params={"set": set_value, "val": value})
        return res.rowcount

    @classmethod
    async def insert(cls, db: Database, table: str, row: dict):
        """ Note that while the values are safe from injection, the column names are not. Ensure the row dict
        is validated using the model and not just passed directly by the user. """

        row_keys, row_keys_vars, _ = _row_keys_vars_set(row)

        query = f"INSERT INTO {table} ({row_keys}) VALUES ({row_keys_vars});"

        return await execute_catch(db, query=query, values=row)

    @classmethod
    async def insert_return_id(cls, db: Database, table: str, row: dict) -> int:
        row_keys, row_keys_vars, _ = _row_keys_vars_set(row)

        query = f"INSERT INTO {table} ({row_keys}) VALUES ({row_keys_vars}) " \
                f"RETURNING (id);"

        return await execute_catch(db, query=query, values=row)

    @classmethod
    async def delete_by_id(cls, db: Database, table: str, id_int: int):
        query = f"DELETE FROM {table} WHERE id = :id"
        return await db.execute(query, values={"id": id_int})

    @classmethod
    async def delete_by_column(cls, db: Database, table: str, column: str, column_val):
        """ The column name is not safe from injections, be sure it is always defined by the server! """

        query = f"DELETE FROM {table} WHERE {column} = :{column}"
        return await db.execute(query, values={column: column_val})

    @classmethod
    async def delete_insert_return_id_transaction(cls, db: Database, table: str, id_int_delete: int, new_row: dict) -> int:
        async with db.transaction():
            await cls.delete_by_id(db, table, id_int_delete)
            returned_id = await cls.insert_return_id(db, table, new_row)
        return returned_id

    @classmethod
    async def double_insert_transaction(cls, db: Database, first_table: str, first_row: dict, second_table: str,
                                        second_row: dict):
        """ Used for adding to two tables, where the second requires the id from the first. """
        async with db.transaction():
            id_int = await cls.insert_return_id(db, first_table, first_row)
            second_row['id'] = id_int
            returned = await cls.insert(db, second_table, second_row)
        return returned
