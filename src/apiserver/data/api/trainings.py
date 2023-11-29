from datetime import date
from apiserver.lib.utilities import usp_hex
from schema.model.model import C_EVENTS_CATEGORY, C_EVENTS_DATE, C_EVENTS_DESCRIPTION, C_EVENTS_ID, CLASS_EVENTS_TABLE, CLASS_ID, MAX_EVENT_ID_LEN
from store.conn import AsyncConenctionContext
from store.db import LiteralDict, insert_many
from store.error import DataError

async def add_training_event(
    conn: AsyncConenctionContext,
    classification_id: int,
    categories: list[str],
    event_date: date,
    description: str = "",
) -> list[str]:
    """breaks up a training into their subcategories and insert them into the class_events table.
    event_id will be created in the form of: "training[dd/mm/yyyy][category]"
    we make the assumption that there are no two trainings in a day"""
    idList = [str]
    event_rows = [LiteralDict]
    for subCategory in categories:
        subEventId = usp_hex(f'training{event_date.isoformat()}{subCategory}')

        if len(subEventId) > MAX_EVENT_ID_LEN:
            raise DataError(
                f"event_id is longer than {MAX_EVENT_ID_LEN}! Please use a short,"
                " descriptive name, like 'nsk_weg_2023'.",
                "event_id_too_long",
            )
        idList.append(subEventId)

        event_row: LiteralDict = {
            C_EVENTS_ID: subEventId,
            CLASS_ID: classification_id,
            C_EVENTS_CATEGORY: subCategory,
            C_EVENTS_DATE: event_date,
            C_EVENTS_DESCRIPTION: description,
        }
        event_rows.append[event_row]

    await insert_many(conn, CLASS_EVENTS_TABLE, event_rows)
    
    return idList
