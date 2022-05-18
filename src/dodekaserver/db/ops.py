from abc import ABC, abstractmethod
from typing import Optional

from databases import Database


class DbOperations(ABC):
    """
    The DbOperations class provides an easily referencable object that can be mocked.
    This circumvents a problem where mocks are ignored as FastAPI changes the function
    references at startup.
    """
    @classmethod
    @abstractmethod
    async def retrieve_by_id(cls, db: Database, table: str, id_int: int) -> Optional[dict]:
        ...

    @classmethod
    @abstractmethod
    async def retrieve_by_unique(cls, db: Database, table: str, unique_column: str, value) -> Optional[dict]:
        ...

    @classmethod
    @abstractmethod
    async def upsert_by_id(cls, db: Database, table: str, row: dict):
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
