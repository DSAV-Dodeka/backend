import datetime

from pydantic import BaseModel
from starlette.requests import Request

from apiserver import data
from apiserver.app.ops.header import Authorization
from apiserver.app.routers.admin import router
from apiserver.app.routers.helper import require_admin
from apiserver.data import Source
from apiserver.data.api.classifications import check_user_in_class


class UserPoints(BaseModel):
    user_id: str
    points: int


class RankingUpdate(BaseModel):
    users: list[UserPoints]
    classification_id: int
    category: str
    description: str = "Empty"
    date: datetime.date
    event: str


@router.post("/admin/ranking/update/")
async def update_ranking(
    update: RankingUpdate, request: Request, authorization: Authorization
):
    dsrc: Source = request.state.dsrc
    await require_admin(authorization, dsrc)

    # Add points per user to class_events database. (loop)
    # Before adding the points I should check if the date
    # on the date on the update_ranking is within
    # the given timeframe.
    async with data.get_conn(dsrc) as conn:
        event_id = await data.classifications.add_class_event(
            conn,
            update.classification_id,
            update.category,
            update.description,
            update.date,
        )

        for user in update.users:
            await data.classifications.add_points_to_event(
                conn, event_id, user.user_id, user.points
            )

            # I will check if there exist a row in the database.
            # If on signup and on the creation of the classification
            # you add a row with value zero that won't be needed.

            # TODO finish
            is_in_database = await check_user_in_class(
                conn, user.user_id, update.classification_id
            )

            # Update or insert in database.

            # See if hidden_date has past.
            # TODO finish
            hidden_date = await data.classifications.get_hidden_date(
                conn, update.classification_id
            )
