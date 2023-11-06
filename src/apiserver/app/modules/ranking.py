from typing import Literal

from pydantic import BaseModel
from datetime import date

from apiserver.app.error import ErrorKeys, AppError
from apiserver.data import Source
from apiserver import data
from apiserver.data.api.classifications import UserPoints
from store.error import DataError


class NewEvent(BaseModel):
    users: list[UserPoints]
    class_type: Literal["points", "training"]
    date: date
    event_id: str
    category: str
    description: str = ""


async def add_new_event(dsrc: Source, new_event: NewEvent) -> None:
    """Add a new event and recompute points. Display points will be updated to not include any events after the hidden
    date. Use the 'publish' function to force them to be equal."""
    async with data.get_conn(dsrc) as conn:
        try:
            classification = await data.classifications.most_recent_class_of_type(
                conn, new_event.class_type
            )
        except DataError as e:
            if e.key != "incorrect_class_type":
                raise e
            raise AppError(ErrorKeys.RANKING_UPDATE, e.message, "incorrect_class_type")
        if classification.start_date > new_event.date:
            desc = "Event cannot happen before start of classification!"
            raise AppError(ErrorKeys.RANKING_UPDATE, desc, "ranking_date_before_start")

        event_id = await data.classifications.add_class_event(
            conn,
            new_event.event_id,
            classification.classification_id,
            new_event.category,
            new_event.date,
            new_event.description,
        )

        try:
            await data.classifications.add_users_to_event(
                conn, event_id=event_id, points=new_event.users
            )
        except DataError as e:
            if e.key != "database_integrity":
                raise e
            raise AppError(
                ErrorKeys.RANKING_UPDATE,
                e.message,
                "add_event_users_violates_integrity",
            )

        await data.special.update_class_points(
            conn,
            classification.classification_id,
        )


async def sync_publish_ranking(dsrc: Source, publish: bool) -> None:
    async with data.get_conn(dsrc) as conn:
        training_class = await data.classifications.most_recent_class_of_type(
            conn, "training"
        )
        points_class = await data.classifications.most_recent_class_of_type(
            conn, "points"
        )
        await data.special.update_class_points(
            conn, training_class.classification_id, publish
        )
        await data.special.update_class_points(
            conn, points_class.classification_id, publish
        )
