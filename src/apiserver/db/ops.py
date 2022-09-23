from abc import ABC, abstractmethod
from typing import Optional

from databases import Database
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncTransaction, AsyncConnection


class DbOperations(ABC):
    """
    The DbOperations class provides an easily referencable object that can be mocked.
    This circumvents a problem where mocks are ignored as FastAPI changes the function
    references at startup.
    """

    @classmethod
    @abstractmethod
    def begin_conn(cls, engine: AsyncEngine) -> AsyncConnection:
        ...

    @classmethod
    @abstractmethod
    async def retrieve_by_id(cls, conn: AsyncConnection, table: str, id_int: int) -> Optional[dict]:
        ...

    @classmethod
    @abstractmethod
    async def retrieve_by_unique(cls, db: Database, table: str, unique_column: str, value) -> Optional[dict]:
        ...

    @classmethod
    async def retrieve_table(cls, db: Database, table: str) -> list[dict]:
        ...

    @classmethod
    @abstractmethod
    async def exists_by_unique(cls, db: Database, table: str, unique_column: str, value) -> bool:
        ...

    @classmethod
    @abstractmethod
    async def upsert_by_id(cls, db: Database, table: str, row: dict):
        ...

    @classmethod
    @abstractmethod
    async def insert(cls, db: Database, table: str, row: dict):
        ...

    @classmethod
    @abstractmethod
    async def insert_return_id(cls, db: Database, table: str, row: dict) -> int:
        ...

    @classmethod
    @abstractmethod
    async def delete_by_id(cls, db: Database, table: str, id_int: int):
        ...

    @classmethod
    @abstractmethod
    async def delete_by_column(cls, db: Database, table: str, column: str, column_val):
        ...

    @classmethod
    @abstractmethod
    async def delete_insert_return_id_transaction(cls, db: Database, table: str, id_int_delete: int, new_row: dict) -> \
            int:
        ...

    @classmethod
    @abstractmethod
    async def double_insert_transaction(cls, db: Database, first_table: str, first_row: dict, second_table: str,
                                        second_row: dict):
        ...


class DbError(Exception):
    """ Exception that represents special internal errors. """
    def __init__(self, err_desc: str, err_internal: str, debug_key: str = None):
        self.err_desc = err_desc
        self.err_internal = err_internal
        self.debug_key = debug_key
