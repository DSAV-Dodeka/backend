from datetime import date
from schema.model.model import C_EVENTS_CATEGORY, C_EVENTS_DATE, C_EVENTS_DESCRIPTION, C_EVENTS_ID, CLASS_EVENTS_TABLE, CLASS_ID
from sqlalchemy.ext.asyncio import AsyncConnection
from store.db import LiteralDict, insert_many

async def add_training_event(
    conn: AsyncConnection,
    classification_id: int,
    categories: list[str],
    event_date: date,
    description: str = "",
) -> list[str]:
    """breaks up a training into their subcategories and insert them into the class_events table.
    event_id will be created in the form of: "training[yyyy/dd/mm][category]"
    we make the assumption that there are no two trainings in a day"""
    idList = []
    event_rows: list[LiteralDict] = []
    for subCategory in categories:
        subEventId = f'training{event_date.isoformat()}{subCategory}'
        idList.append(subEventId)

        event_row: LiteralDict = {
            C_EVENTS_ID: subEventId,
            CLASS_ID: classification_id,
            C_EVENTS_CATEGORY: subCategory,
            C_EVENTS_DATE: event_date,
            C_EVENTS_DESCRIPTION: description,
        }
        event_rows.append(event_row)
    await insert_many(conn, CLASS_EVENTS_TABLE, event_rows)

    return idList
