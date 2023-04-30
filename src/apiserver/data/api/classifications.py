from datetime import date

from sqlalchemy.ext.asyncio import AsyncConnection

from apiserver.data.db.model import CLASSIFICATION_TABLE
from apiserver.lib.model.entities import Classification
from apiserver.data.db.ops import insert_many


async def insert_classification(conn: AsyncConnection):
    a = Classification(
        type="abc",
        last_updated=date.today(),
        start_date=date.today(),
        end_date=date.today(),
        hidden_date=date.today(),
    )
    return await insert_many(conn, CLASSIFICATION_TABLE, [a])
