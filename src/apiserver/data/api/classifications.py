from datetime import date, datetime, timedelta
from typing import Literal, List, Sequence

from fastapi.responses import ORJSONResponse
from pydantic import TypeAdapter
from sqlalchemy import RowMapping
from sqlalchemy.ext.asyncio import AsyncConnection

from apiserver.lib.utilities import usp_hex
from store.error import DataError, NoDataError
from schema.model import (
    CLASSIFICATION_TABLE,
    CLASS_TYPE,
    CLASS_START_DATE,
    CLASS_ID,
    CLASS_POINTS_TABLE,
    DISPLAY_POINTS,
    CLASS_LAST_UPDATED,
    USER_ID,
    USERDATA_TABLE,
    UD_FIRSTNAME,
    UD_LASTNAME,
    C_EVENTS_CATEGORY,
    C_EVENTS_DATE,
    C_EVENTS_DESCRIPTION,
    CLASS_EVENTS_TABLE,
    TRUE_POINTS,
    C_EVENTS_ID,
    C_EVENTS_POINTS,
    CLASS_EVENTS_POINTS_TABLE,
    CLASS_HIDDEN_DATE,
    MAX_EVENT_ID_LEN,
)
from store.db import (
    insert_many,
    get_largest_where,
    select_some_where,
    select_some_join_where,
    insert,
    select_some_two_where,
    insert_return_col,
)
from apiserver.lib.model.entities import (
    Classification,
    ClassView,
    UserPoints,
    UserPointsList,
)


def parse_user_points(user_points: list[RowMapping]) -> list[UserPoints]:
    if len(user_points) == 0:
        raise NoDataError("UserPoints does not exist.", "userpoints_data_empty")
    return UserPointsList.validate_python(user_points)


async def insert_classification(
    conn: AsyncConnection, class_type: str, start_date: date = None
):
    if start_date is None:
        start_date = date.today()
    new_classification = Classification(
        type=class_type,
        last_updated=date.today(),
        start_date=start_date,
        end_date=start_date + timedelta(days=30 * 5),
        hidden_date=start_date + timedelta(days=30 * 4),
    )
    return await insert(conn, CLASSIFICATION_TABLE, new_classification.model_dump())


async def most_recent_class_of_type(
    conn: AsyncConnection, class_type: Literal["training", "points"]
) -> ClassView:
    if class_type == "training":
        query_class_type = "training"
    elif class_type == "points":
        query_class_type = "points"
    else:
        raise DataError(
            "Only training or points classification types supported!",
            "incorrect_class_type",
        )

    largest_class_list = await get_largest_where(
        conn,
        CLASSIFICATION_TABLE,
        {CLASS_ID, CLASS_LAST_UPDATED},
        CLASS_TYPE,
        query_class_type,
        CLASS_START_DATE,
        1,
    )
    if len(largest_class_list) == 0:
        raise NoDataError(
            "No most recent training classification found!",
            "no_most_recent_training_class",
        )

    return ClassView.model_validate(largest_class_list[0])


async def add_class_event(
    conn: AsyncConnection,
    event_id: str,
    classification_id: int,
    category: str,
    event_date: datetime.date,
    description: str = "",
) -> str:
    """It's important they use a descriptive, unique id for the event like 'nsk_weg_2023'. We only accept simple ascii
    strings. The name is also usp_hex'd to ensure it is readable inside the database. It returns the id, which is also
    usp_hex'd."""
    if len(event_id) > MAX_EVENT_ID_LEN:
        raise DataError(
            f"event_id is longer than {MAX_EVENT_ID_LEN}! Please use a short,"
            " descriptive name, like 'nsk_weg_2023'.",
            "event_id_too_long",
        )
    usph_id = usp_hex(event_id)

    event_row = {
        C_EVENTS_ID: usph_id,
        CLASS_ID: classification_id,
        C_EVENTS_CATEGORY: category,
        C_EVENTS_DATE: event_date,
        C_EVENTS_DESCRIPTION: description,
    }

    await insert(conn, CLASS_EVENTS_TABLE, event_row)
    return usph_id


async def upsert_user_event_points(
    conn: AsyncConnection, event_id: int, user_id: str, points: int
):
    row_to_insert = {
        USER_ID: user_id,
        C_EVENTS_ID: event_id,
        C_EVENTS_POINTS: points,
    }

    await insert(conn, CLASS_EVENTS_POINTS_TABLE, row_to_insert)


async def check_user_in_class(
    conn: AsyncConnection,
    user_id: str,
    classification_id: int,
) -> bool:
    data = await select_some_two_where(
        conn,
        CLASS_POINTS_TABLE,
        {TRUE_POINTS},
        USER_ID,
        user_id,
        CLASS_ID,
        classification_id,
    )

    return data is not None


async def get_hidden_date(conn: AsyncConnection, classification_id: int) -> str:
    hidden_date_data = await select_some_where(
        conn, CLASSIFICATION_TABLE, {CLASS_HIDDEN_DATE}, CLASS_ID, classification_id
    )

    print(
        ORJSONResponse([hidden_date.model_dump() for hidden_date in hidden_date_data])
    )
    return "str"
