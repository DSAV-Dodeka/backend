from datetime import date, timedelta
from typing import Literal

from sqlalchemy import RowMapping
from sqlalchemy.ext.asyncio import AsyncConnection

from apiserver.lib.model.entities import (
    ClassEvent,
    Classification,
    ClassView,
    UserPoints,
    UserPointsNames,
    UserPointsNamesList,
    EventsList,
)
from apiserver.lib.utilities import usp_hex
from schema.model import (
    CLASSIFICATION_TABLE,
    CLASS_TYPE,
    CLASS_START_DATE,
    CLASS_ID,
    CLASS_LAST_UPDATED,
    USER_ID,
    C_EVENTS_CATEGORY,
    C_EVENTS_DATE,
    C_EVENTS_DESCRIPTION,
    CLASS_EVENTS_TABLE,
    C_EVENTS_ID,
    C_EVENTS_POINTS,
    CLASS_EVENTS_POINTS_TABLE,
    MAX_EVENT_ID_LEN,
    CLASS_HIDDEN_DATE,
    USERDATA_TABLE,
    DISPLAY_POINTS,
    UD_FIRSTNAME,
    UD_LASTNAME,
    CLASS_POINTS_TABLE,
    TRUE_POINTS,
)
from store.db import (
    LiteralDict,
    get_largest_where,
    insert,
    insert_many,
    lit_model,
    select_some_join_where,
    select_some_where,
)
from store.error import DataError, NoDataError, DbError, DbErrors


def parse_user_points(user_points: list[RowMapping]) -> list[UserPointsNames]:
    if len(user_points) == 0:
        raise NoDataError(
            "UserPointsNames does not exist.", "userpointsnames_data_empty"
        )
    return UserPointsNamesList.validate_python(user_points)


async def insert_classification(
    conn: AsyncConnection, class_type: str, start_date: date | None = None
) -> None:
    if start_date is None:
        start_date = date.today()
    new_classification = Classification(
        type=class_type,
        last_updated=date.today(),
        start_date=start_date,
        end_date=start_date + timedelta(days=30 * 5),
        hidden_date=start_date + timedelta(days=30 * 4),
    )
    await insert(conn, CLASSIFICATION_TABLE, lit_model(new_classification))


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
        {CLASS_ID, CLASS_LAST_UPDATED, CLASS_START_DATE, CLASS_HIDDEN_DATE},
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


async def all_points_in_class(
    conn: AsyncConnection, class_id: int, show_true_points: bool = False
) -> list[UserPointsNames]:
    points_col = DISPLAY_POINTS
    if show_true_points:
        points_col = TRUE_POINTS

    # Necessary because user_id is present in both tables
    user_id_select = f"{USERDATA_TABLE}.{USER_ID}"
    user_points = await select_some_join_where(
        conn,
        {points_col, UD_FIRSTNAME, UD_LASTNAME, user_id_select},
        CLASS_POINTS_TABLE,
        USERDATA_TABLE,
        USER_ID,
        USER_ID,
        CLASS_ID,
        class_id,
    )

    return parse_user_points(user_points)


async def add_class_event(
    conn: AsyncConnection,
    event_id: str,
    classification_id: int,
    category: str,
    event_date: date,
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

    event_row: LiteralDict = {
        C_EVENTS_ID: usph_id,
        CLASS_ID: classification_id,
        C_EVENTS_CATEGORY: category,
        C_EVENTS_DATE: event_date,
        C_EVENTS_DESCRIPTION: description,
    }

    await insert(conn, CLASS_EVENTS_TABLE, event_row)
    return usph_id


async def upsert_user_event_points(
    conn: AsyncConnection, event_id: str, user_id: str, points: int
) -> None:
    row_to_insert: LiteralDict = {
        USER_ID: user_id,
        C_EVENTS_ID: event_id,
        C_EVENTS_POINTS: points,
    }

    await insert(conn, CLASS_EVENTS_POINTS_TABLE, row_to_insert)


async def add_users_to_event(
    conn: AsyncConnection, event_id: str, points: list[UserPoints]
) -> int:
    points_with_events: list[LiteralDict] = [
        {"event_id": event_id, "user_id": up.user_id, "points": up.points}
        for up in points
    ]

    try:
        return await insert_many(conn, CLASS_EVENTS_POINTS_TABLE, points_with_events)
    except DbError as e:
        if e.key == DbErrors.INTEGRITY:
            raise DataError(
                f"Input {points_with_events} violates database integrity, most likely a"
                " duplicate value!",
                "database_integrity",
            )
        raise e


async def events_in_class(conn: AsyncConnection, class_id: int) -> list[ClassEvent]:
    events = await select_some_where(
        conn,
        CLASS_EVENTS_TABLE,
        {C_EVENTS_ID, C_EVENTS_CATEGORY, C_EVENTS_DESCRIPTION, C_EVENTS_DATE},
        CLASS_ID,
        class_id,
    )

    return EventsList.validate_python(events)


async def get_event_user_points(
    conn: AsyncConnection, event_id: str
) -> list[UserPointsNames]:
    """If resulting list is empty, either the event doesn't exist or it has no users in it."""
    user_id_select = f"{USERDATA_TABLE}.{USER_ID}"
    user_points = await select_some_join_where(
        conn,
        {user_id_select, UD_FIRSTNAME, UD_LASTNAME, C_EVENTS_POINTS},
        CLASS_EVENTS_POINTS_TABLE,
        USERDATA_TABLE,
        USER_ID,
        USER_ID,
        C_EVENTS_ID,
        event_id,
    )

    return UserPointsNamesList.validate_python(user_points)
