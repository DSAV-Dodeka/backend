from abc import ABC, abstractmethod
from typing import Optional, Any

from databases import Database
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncConnection


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
    async def retrieve_by_unique(cls, conn: AsyncConnection, table: str, unique_column: str, value) -> Optional[dict]:
        ...

    @classmethod
    @abstractmethod
    async def fetch_column_by_unique(cls, conn: AsyncConnection, table: str, fetch_column: str, unique_column: str,
                                     value) -> Optional[Any]:
        ...

    @classmethod
    @abstractmethod
    async def select_where(cls, conn: AsyncConnection, table: str, column, value) -> list[dict]:
        ...

    @classmethod
    @abstractmethod
    async def retrieve_table(cls, db: Database, table: str) -> list[dict]:
        ...

    @classmethod
    @abstractmethod
    async def exists_by_unique(cls, db: Database, table: str, unique_column: str, value) -> bool:
        ...

    @classmethod
    @abstractmethod
    async def upsert_by_unique(cls, conn: AsyncConnection, table: str, row: dict, unique_column: str) -> int:
        ...

    @classmethod
    @abstractmethod
    async def upsert_by_id(cls, db: Database, table: str, row: dict):
        ...

    @classmethod
    async def update_column_by_unique(cls, conn: AsyncConnection, table: str, set_column: str, set_value,
                                      unique_column: str, value) -> int:
        ...

    @classmethod
    @abstractmethod
    async def insert(cls, db: Database, table: str, row: dict):
        ...

    @classmethod
    @abstractmethod
    async def insert_return_col(cls, db: AsyncConnection, table: str, row: dict, return_col: str) -> Any:
        ...

    @classmethod
    @abstractmethod
    async def delete_by_id(cls, conn: AsyncConnection, table: str, id_int: int) -> int:
        ...

    @classmethod
    @abstractmethod
    async def delete_by_column(cls, db: Database, table: str, column: str, column_val):
        ...


class DbError(Exception):
    """ Exception that represents special internal errors. """
    def __init__(self, err_desc: str, err_internal: str, debug_key: str = None):
        self.err_desc = err_desc
        self.err_internal = err_internal
        self.debug_key = debug_key
