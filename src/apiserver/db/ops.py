from abc import ABC, abstractmethod
from typing import Optional, Any, AsyncIterator, Callable

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncConnection


class DbOperations(ABC):
    """
    The DbOperations class provides an easily referencable object that can be mocked.
    This circumvents a problem where mocks are ignored as FastAPI changes the function
    references at startup.
    """

    @classmethod
    @abstractmethod
    def begin_conn(cls, engine: AsyncEngine) -> AsyncIterator[AsyncConnection]:
        ...

    @classmethod
    @abstractmethod
    async def retrieve_by_id(
        cls, conn: AsyncConnection, table: str, id_int: int
    ) -> Optional[dict]:
        ...

    @classmethod
    @abstractmethod
    async def retrieve_by_unique(
        cls, conn: AsyncConnection, table: str, unique_column: str, value
    ) -> Optional[dict]:
        ...

    @classmethod
    @abstractmethod
    async def select_some_where(
        cls,
        conn: AsyncConnection,
        table: str,
        sel_col: set[str],
        where_col: str,
        where_value,
    ) -> list[dict]:
        ...

    @classmethod
    @abstractmethod
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
        ...

    @classmethod
    @abstractmethod
    async def select_where(
        cls, conn: AsyncConnection, table: str, column, value
    ) -> list[dict]:
        ...

    @classmethod
    @abstractmethod
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
        ...

    @classmethod
    @abstractmethod
    async def exists_by_unique(
        cls, conn: AsyncConnection, table: str, unique_column: str, value
    ) -> bool:
        ...

    @classmethod
    @abstractmethod
    async def upsert_by_unique(
        cls, conn: AsyncConnection, table: str, row: dict, unique_column: str
    ) -> int:
        ...

    @classmethod
    @abstractmethod
    async def update_column_by_unique(
        cls,
        conn: AsyncConnection,
        table: str,
        set_column: str,
        set_value,
        unique_column: str,
        value,
    ) -> int:
        ...

    @classmethod
    @abstractmethod
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
        ...

    @classmethod
    @abstractmethod
    async def insert(cls, conn: AsyncConnection, table: str, row: dict) -> int:
        ...

    @classmethod
    @abstractmethod
    async def insert_return_col(
        cls, db: AsyncConnection, table: str, row: dict, return_col: str
    ) -> Any:
        ...

    @classmethod
    @abstractmethod
    async def delete_by_id(cls, conn: AsyncConnection, table: str, id_int: int) -> int:
        ...

    @classmethod
    @abstractmethod
    async def delete_by_column(
        cls, conn: AsyncConnection, table: str, column: str, column_val
    ) -> int:
        ...


class DbError(Exception):
    """Exception that represents special internal errors."""

    def __init__(self, err_desc: str, err_internal: str, debug_key: str = None):
        self.err_desc = err_desc
        self.err_internal = err_internal
        self.debug_key = debug_key
