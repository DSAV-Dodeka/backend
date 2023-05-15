from datetime import date
from typing import Literal

from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncConnection

from apiserver.data import DataError
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
    UD_LASTNAME,
)
from apiserver.data.db.ops import (
    insert_many,
    get_largest_where,
    select_some_where,
    select_some_join_where,
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
