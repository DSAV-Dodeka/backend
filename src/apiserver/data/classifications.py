from datetime import date

from sqlalchemy.ext.asyncio import AsyncConnection

from apiserver.db.model import KLASSEMENT_CLASSIFICATION_TABLE
from apiserver.define.entities import Classification
from apiserver.db.db import insert_many


async def insert_classification(conn: AsyncConnection):
    a = Classification(
        type="abc",
        last_updated=date.today(),
        start_date=date.today(),
        end_date=date.today(),
        hidden_date=date.today(),
    )
    await insert_many(conn, KLASSEMENT_CLASSIFICATION_TABLE, [a])
