import asyncio
from typing import Optional

from databases import Database


__all__ = ['DatabaseOperations', 'execute_queries_unsafe']


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


class DatabaseOperations:
    """
    The DatabaseOperations class provides an easily referencable object that can be mocked.
    This circumvents a problem where mocks are ignored as FastAPI changes the function
    references at startup.
    """
    @classmethod
    async def retrieve_by_id(cls, db: Database, table: str, id_int: int) -> Optional[dict]:
        """ Ensure `table` is never user-defined. """
        query = f"SELECT * FROM {table} WHERE id = :id"
        record = await db.fetch_one(query, values={"id": id_int})
        return dict(record) if record is not None else None

    @classmethod
    async def retrieve_by_unique(cls, db: Database, table: str, unique_column: str, value) -> Optional[dict]:
        """ Ensure `unique_column` and `table` are never user-defined. """
        query = f"SELECT * FROM {table} WHERE {unique_column} = :val"
        record = await db.fetch_one(query, values={"val": value})
        return dict(record) if record is not None else None

    @classmethod
    async def upsert_by_id(cls, db: Database, table: str, row: dict):
        """ Note that while the values are safe from injection, the column names are not. Ensure the row dict
        is validated using the model and not just passed directly by the user. """

        row_keys, row_keys_vars, row_keys_set = _row_keys_vars_set(row)

        query = f"INSERT INTO {table} ({row_keys}) VALUES ({row_keys_vars}) ON CONFLICT (id) DO UPDATE SET " \
                f"{row_keys_set};"

        return await db.execute(query=query, values=row)

    @classmethod
    async def insert_return_id(cls, db: Database, table: str, row: dict) -> int:
        row_keys, row_keys_vars, _ = _row_keys_vars_set(row)

        query = f"INSERT INTO {table} ({row_keys}) VALUES ({row_keys_vars}) " \
                f"RETURNING (id);"

        return await db.execute(query=query, values=row)

    @classmethod
    async def delete_by_id(cls, db: Database, table: str, id_int: int):
        query = f"DELETE FROM {table} WHERE id = :id"
        return await db.execute(query, values={"id": id_int})

    @classmethod
    async def delete_insert_return_id_transaction(cls, db: Database, table: str, id_int_delete: int, new_row: dict) -> int:
        async with db.transaction():
            await cls.delete_by_id(db, table, id_int_delete)
            returned_id = await cls.insert_return_id(db, table, new_row)
        return returned_id
