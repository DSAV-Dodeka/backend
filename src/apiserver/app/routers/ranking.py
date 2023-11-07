from typing import Literal, TypeGuard, Optional
from fastapi import APIRouter
from starlette.requests import Request

from apiserver import data
from apiserver.app.error import ErrorResponse, AppError
from apiserver.app.modules.ranking import (
    add_new_event,
    NewEvent,
    sync_publish_ranking,
    class_id_or_recent,
)
from apiserver.app.ops.header import Authorization
from apiserver.app.response import RawJSONResponse
from apiserver.app.routers.helper import require_admin, require_member
from apiserver.lib.model.entities import (
    UserPointsNames,
    UserPointsNamesList,
    UserEventsList,
    EventsList,
)
from apiserver.data import Source, get_conn
from apiserver.data.api.classifications import events_in_class, get_event_user_points
from apiserver.data.special import user_events_in_class

router = APIRouter()


@router.post("/admin/ranking/update/")
async def admin_update_ranking(
    new_event: NewEvent, request: Request, authorization: Authorization
) -> None:
    dsrc: Source = request.state.dsrc
    await require_admin(authorization, dsrc)

    try:
        await add_new_event(dsrc, new_event)
    except AppError as e:
        raise ErrorResponse(400, "invalid_ranking_update", e.err_desc, e.debug_key)


def is_rank_type(rank_type: str) -> TypeGuard[Literal["training", "points"]]:
    return rank_type in {"training", "points"}


async def get_classification(
    dsrc: Source, rank_type: str, admin: bool = False
) -> RawJSONResponse:
    if not is_rank_type(rank_type):
        reason = f"Ranking {rank_type} is unknown!"
        raise ErrorResponse(
            status_code=400,
            err_type="invalid_ranking",
            err_desc=reason,
            debug_key="bad_ranking",
        )
    async with data.get_conn(dsrc) as conn:
        class_view = await data.classifications.most_recent_class_of_type(
            conn, rank_type
        )
        user_points = await data.classifications.all_points_in_class(
            conn, class_view.classification_id, admin
        )
    return RawJSONResponse(UserPointsNamesList.dump_json(user_points))


@router.get(
    "/members/classification/{rank_type}/", response_model=list[UserPointsNames]
)
async def member_classification(
    rank_type: str, request: Request, authorization: Authorization
) -> RawJSONResponse:
    dsrc: Source = request.state.dsrc
    await require_member(authorization, dsrc)

    return await get_classification(dsrc, rank_type, False)


@router.get("/admin/classification/{rank_type}/", response_model=list[UserPointsNames])
async def member_classification_admin(
    rank_type: str, request: Request, authorization: Authorization
) -> RawJSONResponse:
    dsrc: Source = request.state.dsrc
    await require_admin(authorization, dsrc)

    return await get_classification(dsrc, rank_type, True)


@router.post("/admin/class/sync/")
async def sync_publish_classification(
    request: Request, authorization: Authorization, publish: Optional[str] = None
):
    dsrc: Source = request.state.dsrc
    await require_admin(authorization, dsrc)

    do_publish = publish == "publish"
    await sync_publish_ranking(dsrc, do_publish)


@router.get("/admin/class/events/user/{user_id}/")
async def get_user_events_in_class(
    user_id: str,
    request: Request,
    authorization: Authorization,
    class_id: Optional[int] = None,
    rank_type: Optional[str] = None,
):
    dsrc: Source = request.state.dsrc
    await require_admin(authorization, dsrc)

    try:
        sure_class_id = await class_id_or_recent(dsrc, class_id, rank_type)
    except AppError as e:
        raise ErrorResponse(400, e.err_type, e.err_desc, e.debug_key)

    async with get_conn(dsrc) as conn:
        user_events = await user_events_in_class(conn, user_id, sure_class_id)

    return RawJSONResponse(UserEventsList.dump_json(user_events))


@router.get("/admin/class/events/")
async def get_events_in_class(
    request: Request,
    authorization: Authorization,
    class_id: Optional[int] = None,
    rank_type: Optional[str] = None,
):
    dsrc: Source = request.state.dsrc
    await require_admin(authorization, dsrc)

    try:
        sure_class_id = await class_id_or_recent(dsrc, class_id, rank_type)
    except AppError as e:
        raise ErrorResponse(400, e.err_type, e.err_desc, e.debug_key)

    async with get_conn(dsrc) as conn:
        events = await events_in_class(conn, sure_class_id)

    return RawJSONResponse(EventsList.dump_json(events))


@router.get("/admin/class/events/{event_id}/")
async def get_event_users(
    event_id: str, request: Request, authorization: Authorization
):
    dsrc: Source = request.state.dsrc
    await require_admin(authorization, dsrc)

    async with get_conn(dsrc) as conn:
        event_users = await get_event_user_points(conn, event_id)

    return RawJSONResponse(UserPointsNamesList.dump_json(event_users))
