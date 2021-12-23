import asyncio
from typing import Optional

from databases import Database


__all__ = ['DatabaseOperations', 'execute_queries_unsafe']


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
    @staticmethod
    async def retrieve_by_id(db: Database, table: str, id_int: int) -> Optional[dict]:
        """ Ensure `table` is never user-defined. """
        query = f"SELECT * FROM {table} WHERE id = :id"
        record = await db.fetch_one(query, values={"id": id_int})
        return dict(record) if record is not None else None

    @staticmethod
    async def retrieve_by_unique(db: Database, table: str, unique_column: str, value):
        """ Ensure `unique_column` and `table` are never user-defined. """
        query = f"SELECT * FROM {table} WHERE {unique_column} = :val"
        record = await db.fetch_one(query, values={"val": value})
        return dict(record) if record is not None else None

    @staticmethod
    async def upsert_by_id(db: Database, table: str, row: dict):
        """ Note that while the values are safe from injection, the column names are not. Ensure the row dict
        is validated using the model and not just passed directly by the user. """
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
        query = f"INSERT INTO {table} ({row_keys}) VALUES ({row_keys_vars}) ON CONFLICT (id) DO UPDATE SET " \
                f"{row_keys_set};"

        return await db.execute(query=query, values=row)
