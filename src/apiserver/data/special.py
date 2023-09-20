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
    CLASS_EVENTS_POINTS_TABLE,
)
from store.db import execute_catch_conn, row_cnt


async def update_class_points(
    conn: AsyncConnection, class_id: int, update_display: bool
) -> int:
    """
    This is a complex query. What it does, in essence, is collect all the events related to a specific classification_id
    and (in the `class_events` table) add up all the points that each person have over all events in that
    classification. Their point totals for that classification are then updated in the `class_points` table, so they
    can be more easily queried. Furthermore, if `update_display` is False, their display_points will be zero if they
    do not yet exist in the `class_events` table, and will remain unchanged if they already existed. See below for
    more details on the query itself.
    """
    display_points = "0"
    set_display = ""
    if update_display:
        display_points = "new_points"
        set_display = f", {DISPLAY_POINTS} = excluded.{DISPLAY_POINTS}"

    # The outer query is a simple upsert query. We INSERT INTO `class_points` and ON_CONFLICT, we update the true
    # points. We access this from the special `excluded` table, which is the row you are trying to insert but that is
    # conflicting. If update_display is False, we do not also update the `display_points`.

    # The first nested query is a simple SELECT that adds ensures the row we insert into `class_points` has the right
    # columns. We again add te `:id` param to the row. If `update_display` is true, we set the fourth column also
    # equal to `new_points`, otherwise we set it to zero (which, if there is no conflict, so if there is someone new,
    # will add their row with zero points).

    # The second nested query is where the magic happens. It FULL JOINs two nested SELECT statements. Let's discuss the
    # first one. It selects the event_id, user_id and points from the JOIN of the class_events_points and the
    # class_events. This is necessary as only the latter contains the class_id, from which we only take the event_id's
    # that are of the correct class_id.
    # The second nested select takes all user_id's that are listed to be 'active'. The FULL JOIN means that if there are
    # rows that do not match (so if there is an active user with no associated events), it will be added with null for
    # the missing column (so null for event_id and points). We now have a table with multiple events per person,
    # some people with null events and null points. To get the total amount of points per person, we aggregate using
    # the SUM function, and use GROUP BY user_id since we want to take those together. We use the COALESCE(points, 0)
    # to ensure that null values are turned into zeros. The result is a table with only one occurrence of a user_id
    # and that person's points, which is then used by the outermost queries as described above.

    query = text(f"""
        INSERT INTO {CLASS_POINTS_TABLE} ({USER_ID}, {CLASS_ID}, {TRUE_POINTS}, {DISPLAY_POINTS})
        (
            SELECT sm.id, :id, new_points, {display_points} FROM
            (
                SELECT ud.id, SUM(COALESCE(points, 0)) as new_points FROM
                (
                    SELECT ev.{C_EVENTS_ID}, uev.{USER_ID} as id, uev.{C_EVENTS_POINTS} as points 
                    FROM
                        {CLASS_EVENTS_POINTS_TABLE} as uev
                    JOIN
                        (SELECT {C_EVENTS_ID} FROM {CLASS_EVENTS_TABLE} WHERE {CLASS_ID} = :id) as ev
                    ON uev.{C_EVENTS_ID} = ev.{C_EVENTS_ID}
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
