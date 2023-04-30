from datetime import date

from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncConnection

from apiserver.data import DataError
from apiserver.data.db.model import (
    CLASSIFICATION_TABLE,
    CLASS_TYPE,
    CLASS_START_DATE,
    CLASS_ID,
)
from apiserver.data.db.ops import insert_many, get_largest_where
from apiserver.lib.model.entities import Classification


async def insert_classification(conn: AsyncConnection):
    a = Classification(
        type="abc",
        last_updated=date.today(),
        start_date=date.today(),
        end_date=date.today(),
        hidden_date=date.today(),
    )
    return await insert_many(conn, CLASSIFICATION_TABLE, [a])


class ClassId(BaseModel):
    classification_id: int


async def most_recent_training_id(conn: AsyncConnection) -> int:
    largest_id_list = await get_largest_where(
        conn,
        CLASSIFICATION_TABLE,
        {CLASS_ID},
        CLASS_TYPE,
        "training",
        CLASS_START_DATE,
        1,
    )
    if len(largest_id_list) == 0:
        raise DataError(
            "No most recent training classification found!",
            "no_most_recent_training_class",
        )

    return ClassId.parse_obj(largest_id_list[0]).classification_id
