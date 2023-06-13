from datetime import date, datetime
from typing import Literal, Optional

from fastapi.responses import ORJSONResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncConnection

from apiserver.data import DataError, NoDataError
from apiserver.data.db.model import (
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
    UD_LASTNAME, C_EVENTS_CATEGORY, C_EVENTS_DATE, C_EVENTS_DESCRIPTION, CLASS_EVENTS_TABLE,
    TRUE_POINTS, C_EVENTS_ID, C_EVENTS_POINTS_POINTS, CLASS_EVENTS_POINTS_TABLE, CLASS_HIDDEN_DATE,
)
from apiserver.data.db.ops import (
    insert_many,
    get_largest_where,
    select_some_where,
    select_some_join_where, insert, retrieve_by_unique, select_some_two_where, insert_return_col,
)
from apiserver.lib.model.entities import Classification, ClassView, UserPoints


async def insert_classification(conn: AsyncConnection):
    a = Classification(
        type="abc",
        last_updated=date.today(),
        start_date=date.today(),
        end_date=date.today(),
        hidden_date=date.today(),
    )
    return await insert_many(conn, CLASSIFICATION_TABLE, [a])


async def recent_class_id_updated(
        conn: AsyncConnection, class_type: Literal["training"] | Literal["points"]
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
        raise DataError(
            "No most recent training classification found!",
            "no_most_recent_training_class",
        )

    return ClassView.parse_obj(largest_class_list[0])


async def all_points_in_class(conn: AsyncConnection, class_id: int) -> list[UserPoints]:
    user_points = await select_some_join_where(
        conn,
        {DISPLAY_POINTS, UD_FIRSTNAME, UD_LASTNAME},
        CLASS_POINTS_TABLE,
        USERDATA_TABLE,
        USER_ID,
        USER_ID,
        CLASS_ID,
        class_id,
    )

    return [
        UserPoints(points=u[DISPLAY_POINTS], name=f"{u[UD_FIRSTNAME]} {u[UD_LASTNAME]}")
        for u in user_points
    ]


async def add_class_event(
        conn: AsyncConnection,
        classification_id: int,
        category: str,
        description: str,
        event_date: datetime.date,
) -> int:
    points_row = {
        CLASS_ID: classification_id,
        C_EVENTS_CATEGORY: category,
        C_EVENTS_DATE: event_date,
    }
    if description != "Empty":
        points_row[C_EVENTS_DESCRIPTION] = description

    return await insert_return_col(conn, CLASS_EVENTS_TABLE, points_row, C_EVENTS_ID)


async def add_points_to_event(
        conn: AsyncConnection,
        event_id: int,
        user_id: str,
        points: int
):
    row_to_insert = {
        USER_ID: user_id,
        C_EVENTS_ID: event_id,
        C_EVENTS_POINTS_POINTS: points
    }

    await insert(conn, CLASS_EVENTS_POINTS_TABLE, row_to_insert)
    return


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
        classification_id
    )

    return data is not None


async def get_hidden_date(
        conn: AsyncConnection,
        classification_id: int
) -> str:

    hidden_date_data = await select_some_where(
        conn,
        CLASSIFICATION_TABLE,
        {CLASS_HIDDEN_DATE},
        CLASS_ID,
        classification_id
    )

    print(ORJSONResponse([hidden_date.dict() for hidden_date in hidden_date_data]))
    return "str"
