from sqlalchemy import text, RowMapping
from sqlalchemy.ext.asyncio import AsyncConnection

from apiserver.lib.model.entities import UserEventsList, UserEvent
from schema.model import (
    CLASSIFICATION_TABLE,
    C_EVENTS_DATE,
    CLASS_HIDDEN_DATE,
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
    C_EVENTS_CATEGORY,
    C_EVENTS_DESCRIPTION,
)
from store.db import execute_catch_conn, row_cnt, all_rows


async def update_class_points(
    conn: AsyncConnection, class_id: int, publish: bool = False
) -> int:
    """
    This is a complex query. What it does, in essence, is collect all the events related to a specific classification_id
    and (in the `class_events` table) add up all the points that each person have over all events in that
    classification. Their point totals for that classification are then updated in the `class_points` table, so they
    can be more easily queried. Furthermore, if `publish` is True, display_points will also include the events after
    the hidden date. See below for more details on the query itself.
    """
    set_display = "new_points"
    if publish:
        set_display = "new_points_hidden"

    # The outer query is a simple upsert query. We INSERT INTO `class_points` and ON_CONFLICT, we update the true
    # points and display points. We access this from the special `excluded` table, which is the row you are trying to
    # insert but that is conflicting.

    # The first nested query is a simple SELECT that adds ensures the row we insert into `class_points` has the right
    # columns. We again add te `:id` param to the row. If `publish` is true, we set the fourth column also equal to
    # `new_points_hidden`, otherwise we set it `new_points`, which only includes points from events before the hidden
    # date.

    # The second nested query is where the magic happens. It FULL JOINs two nested SELECT statements. Let's discuss the
    # first SELECT. It selects the event_id, user_id and the hidden_points and vis_points. We added columns whether an
    # event is hidden or not and multiply that with the points to get zero or the correct/hidden points. These come
    # from the JOIN of the class_event_points with the events, where we modified the events by joining it with the
    # classification table to separate hidden from non-hidden events. This is also necessary as only the class_events
    # contains the class_id, from which we only take the event_id's that are of the correct class_id.

    # The second nested select takes all user_id's that are listed to be 'active'. The FULL JOIN means that if there are
    # rows that do not match (so if there is an active user with no associated events), it will be added with null for
    # the missing column (so null for event_id and points). We now have a table with multiple events per person,
    # some people with null events and null points. To get the total amount of points per person, we aggregate using
    # the SUM function, and use GROUP BY user_id since we want to take those together. We use the COALESCE(points, 0)
    # to ensure that null values are turned into zeros. The result is a table with only one occurrence of a user_id
    # and that person's points, which is then used by the outermost queries as described above.

    # Below is the raw query
    """
    INSERT INTO class_points (user_id, classification_id, true_points, display_points)
        (
            SELECT sm.id, :id, new_points_hidden, new_points FROM
            (
                SELECT
                    ud.id,
                    SUM(COALESCE(hidden_points, 0)) as new_points_hidden,
                    SUM(COALESCE(vis_points, 0)) as new_points
                FROM
                (
                    SELECT
                        ev.event_id, uev.user_id as id,
                        uev.points*ev.hidden+uev.points*visible as hidden_points,
                        uev.points*visible as vis_points
                    FROM
                        class_event_points as uev
                    JOIN
                        (
                            SELECT
                                event_id,
                                (ev_all.date < clss.hidden_date)::int as visible,
                                (ev_all.date >= clss.hidden_date)::int as hidden
                            FROM class_events as ev_all
                            JOIN classifications as clss
                            ON ev_all.classification_id = clss.classification_id
                            WHERE ev_all.classification_id = :id
                        ) as ev

                    ON uev.event_id = ev.event_id
                ) as ce
                FULL JOIN
                    (SELECT userdata.user_id as id FROM userdata WHERE active = TRUE) as ud
                ON ud.id = ce.id
                GROUP BY ud.id
            ) as sm
        )
        ON CONFLICT (user_id, classification_id) DO UPDATE SET
        true_points = excluded.true_points,
        display_points = excluded.display_points;
    """

    query = text(f"""
        INSERT INTO {CLASS_POINTS_TABLE} ({USER_ID}, {CLASS_ID}, {TRUE_POINTS}, {DISPLAY_POINTS})
        (
            SELECT sm.id, :id, new_points_hidden, {set_display} FROM
            (
                SELECT
                    ud.id,
                    SUM(COALESCE(hidden_points, 0)) as new_points_hidden,
                    SUM(COALESCE(vis_points, 0)) as new_points
                FROM
                (
                    SELECT
                        ev.{C_EVENTS_ID},
                        uev.{USER_ID} as id,
                        uev.{C_EVENTS_POINTS}*ev.hidden+uev.{C_EVENTS_POINTS}*ev.visible as hidden_points,
                        uev.{C_EVENTS_POINTS}*ev.visible as vis_points
                    FROM
                        {CLASS_EVENTS_POINTS_TABLE} as uev
                    JOIN
                        (
                            SELECT
                                {C_EVENTS_ID},
                                (ev_all.{C_EVENTS_DATE} < clss.{CLASS_HIDDEN_DATE})::int as visible,
                                (ev_all.{C_EVENTS_DATE} >= clss.{CLASS_HIDDEN_DATE})::int as hidden
                            FROM {CLASS_EVENTS_TABLE} as ev_all
                            JOIN {CLASSIFICATION_TABLE} as clss
                            ON ev_all.{CLASS_ID} = clss.{CLASS_ID}
                            WHERE ev_all.{CLASS_ID} = :id
                        ) as ev
                    ON uev.{C_EVENTS_ID} = ev.{C_EVENTS_ID}
                ) as ce
                FULL JOIN
                    (SELECT {USERDATA_TABLE}.{USER_ID} as id FROM {USERDATA_TABLE} WHERE {UD_ACTIVE} = TRUE) as ud
                ON ud.id = ce.id
                GROUP BY ud.id
            ) as sm
        )
        ON CONFLICT ({USER_ID}, {CLASS_ID}) DO UPDATE SET
        {TRUE_POINTS} = excluded.{TRUE_POINTS},
        {DISPLAY_POINTS} = excluded.{DISPLAY_POINTS};
    """)

    res = await execute_catch_conn(conn, query, parameters={"id": class_id})
    return row_cnt(res)


def parse_user_events(user_events: list[RowMapping]) -> list[UserEvent]:
    if len(user_events) == 0:
        return []
    return UserEventsList.validate_python(user_events)


async def user_events_in_class(
    conn: AsyncConnection, user_id: str, class_id: int
) -> list[UserEvent]:
    query = text(f"""
        SELECT cp.{C_EVENTS_ID}, {C_EVENTS_CATEGORY}, {C_EVENTS_DESCRIPTION}, {C_EVENTS_DATE}, {C_EVENTS_POINTS}
        FROM {CLASS_EVENTS_POINTS_TABLE} as cp
        JOIN {CLASS_EVENTS_TABLE} as ce on cp.{C_EVENTS_ID} = ce.{C_EVENTS_ID}
        WHERE ce.{CLASS_ID} = :class AND cp.{USER_ID} = :user;""")
    res = await conn.execute(query, parameters={"class": class_id, "user": user_id})
    return parse_user_events(all_rows(res))
