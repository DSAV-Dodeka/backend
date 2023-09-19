from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection

from schema.model import (
    CLASS_POINTS_TABLE,
    USER_ID,
    CLASS_ID,
    TRUE_POINTS,
    DISPLAY_POINTS,
    CLASS_EVENTS_TABLE,
    UD_ACTIVE,
    C_EVENTS_ID,
    C_EVENTS_POINTS,
    USERDATA_TABLE,
)
from store.db import execute_catch_conn, row_cnt


async def update_class_points(
    conn: AsyncConnection, class_id: int, update_display: bool
):
    display_points = "0"
    set_display = ""
    if update_display:
        display_points = "new_points"
        set_display = f", {DISPLAY_POINTS} = excluded.{DISPLAY_POINTS}"
    query = text(f"""
        INSERT INTO {CLASS_POINTS_TABLE} ({USER_ID}, {CLASS_ID}, {TRUE_POINTS}, {DISPLAY_POINTS})
        (
            SELECT sm.id, :id, new_points, {display_points} FROM
            (
                SELECT ud.id, SUM(COALESCE(points, 0)) as new_points FROM
                (
                    SELECT {C_EVENTS_ID}, {USER_ID} as id, {C_EVENTS_POINTS} as points 
                    FROM {CLASS_EVENTS_TABLE} WHERE {CLASS_ID} = :id
                ) as ce
                FULL JOIN
                        (SELECT {USERDATA_TABLE}.{USER_ID} as id FROM {USERDATA_TABLE} WHERE {UD_ACTIVE} = TRUE) as ud
                ON ud.id = ce.id
                GROUP BY ud.id
            ) as sm
        )
        ON CONFLICT ({USER_ID}, {CLASS_ID}) DO UPDATE SET 
        {TRUE_POINTS} = excluded.{TRUE_POINTS}
        {set_display};
    """)

    res = await execute_catch_conn(conn, query, params={"id": class_id})
    return row_cnt(res)
