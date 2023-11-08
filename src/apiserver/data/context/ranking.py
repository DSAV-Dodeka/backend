from datacontext.context import ContextRegistry
from typing import Literal

from store.error import DataError

from apiserver.lib.model.entities import (
    ClassEvent,
    ClassView,
    NewEvent,
    UserEvent,
    UserPointsNames,
)
from apiserver.data import Source
from apiserver.data.api.classifications import (
    add_class_event,
    add_users_to_event,
    all_points_in_class,
    events_in_class,
    get_event_user_points,
    most_recent_class_of_type,
)
from apiserver.data.context import RankingContext
from apiserver.data.source import get_conn
from apiserver.data.special import update_class_points, user_events_in_class
from apiserver.app.error import ErrorKeys, AppError


ctx_reg = ContextRegistry()


def check_add_to_class(classification: ClassView, new_event: NewEvent) -> None:
    """Throws AppError if not correct."""
    if classification.start_date > new_event.date:
        desc = "Event cannot happen before start of classification!"
        raise AppError(ErrorKeys.RANKING_UPDATE, desc, "ranking_date_before_start")


@ctx_reg.register(RankingContext)
async def add_new_event(dsrc: Source, new_event: NewEvent) -> None:
    """Add a new event and recompute points. Display points will be updated to not include any events after the hidden
    date. Use the 'publish' function to force them to be equal."""
    async with get_conn(dsrc) as conn:
        try:
            classification = await most_recent_class_of_type(conn, new_event.class_type)
        except DataError as e:
            if e.key != "incorrect_class_type":
                raise e
            raise AppError(ErrorKeys.RANKING_UPDATE, e.message, "incorrect_class_type")

        # THROWS AppError
        check_add_to_class(classification, new_event)

        event_id = await add_class_event(
            conn,
            new_event.event_id,
            classification.classification_id,
            new_event.category,
            new_event.date,
            new_event.description,
        )

        try:
            await add_users_to_event(conn, event_id=event_id, points=new_event.users)
        except DataError as e:
            if e.key != "database_integrity":
                raise e
            raise AppError(
                ErrorKeys.RANKING_UPDATE,
                e.message,
                "add_event_users_violates_integrity",
            )

        await update_class_points(
            conn,
            classification.classification_id,
        )


@ctx_reg.register(RankingContext)
async def context_most_recent_class_id_of_type(
    dsrc: Source, rank_type: Literal["points", "training"]
) -> int:
    async with get_conn(dsrc) as conn:
        class_id = (await most_recent_class_of_type(conn, rank_type)).classification_id

    return class_id


@ctx_reg.register(RankingContext)
async def context_most_recent_class_points(
    dsrc: Source, rank_type: Literal["points", "training"], is_admin: bool
) -> list[UserPointsNames]:
    async with get_conn(dsrc) as conn:
        class_view = await most_recent_class_of_type(conn, rank_type)
        user_points = await all_points_in_class(
            conn, class_view.classification_id, is_admin
        )

    return user_points


@ctx_reg.register(RankingContext)
async def sync_publish_ranking(dsrc: Source, publish: bool) -> None:
    async with get_conn(dsrc) as conn:
        training_class = await most_recent_class_of_type(conn, "training")
        points_class = await most_recent_class_of_type(conn, "points")
        await update_class_points(conn, training_class.classification_id, publish)
        await update_class_points(conn, points_class.classification_id, publish)


@ctx_reg.register(RankingContext)
async def context_user_events_in_class(
    dsrc: Source, user_id: str, class_id: int
) -> list[UserEvent]:
    async with get_conn(dsrc) as conn:
        user_events = await user_events_in_class(conn, user_id, class_id)

    return user_events


@ctx_reg.register(RankingContext)
async def context_events_in_class(dsrc: Source, class_id: int) -> list[ClassEvent]:
    async with get_conn(dsrc) as conn:
        events = await events_in_class(conn, class_id)

    return events


@ctx_reg.register(RankingContext)
async def context_get_event_users(dsrc: Source, event_id: str) -> list[UserPointsNames]:
    """If resulting list is empty, either the event doesn't exist or it has no users in it."""
    async with get_conn(dsrc) as conn:
        events_points = await get_event_user_points(conn, event_id)

    return events_points
