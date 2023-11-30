from typing import Optional
from fastapi import APIRouter
from apiserver.app.dependencies import AppContext, SourceDep

from datacontext.context import ctxlize_wrap
from apiserver.app.error import ErrorResponse, AppError
from apiserver.app.modules.ranking import (
    mod_events_in_class,
    mod_user_events_in_class,
)
from apiserver.app.response import RawJSONResponse
from apiserver.data.api.classifications import get_event_user_points
from apiserver.data import Source
from apiserver.data.context.app_context import RankingContext, conn_wrap
from apiserver.data.context.ranking import (
    add_new_event,
    context_most_recent_class_points,
    sync_publish_ranking,
)
from apiserver.lib.logic.ranking import is_rank_type
from apiserver.lib.model.entities import (
    ClassEvent,
    NewEvent,
    UserEvent,
    UserPointsNames,
    UserPointsNamesList,
    UserEventsList,
    EventsList,
)


old_router = APIRouter(tags=["ranking"])
ranking_admin_router = APIRouter(prefix="/class", tags=["ranking"])
ranking_members_router = APIRouter(prefix="/class", tags=["ranking"])


@old_router.get("/admin/ranking/update/")
async def admin_update_ranking_old(
    new_event: NewEvent, dsrc: SourceDep, app_context: AppContext
) -> None:
    return await admin_update_ranking(new_event, dsrc, app_context)


@ranking_admin_router.post("/update/")
async def admin_update_ranking(
    new_event: NewEvent, dsrc: SourceDep, app_context: AppContext
) -> None:
    try:
        await add_new_event(app_context.rank_ctx, dsrc, new_event)
    except AppError as e:
        raise ErrorResponse(400, "invalid_ranking_update", e.err_desc, e.debug_key)


async def get_classification(
    dsrc: Source, ctx: RankingContext, rank_type: str, admin: bool = False
) -> RawJSONResponse:
    if not is_rank_type(rank_type):
        reason = f"Ranking {rank_type} is unknown!"
        raise ErrorResponse(
            status_code=400,
            err_type="invalid_ranking",
            err_desc=reason,
            debug_key="bad_ranking",
        )

    user_points = await context_most_recent_class_points(ctx, dsrc, rank_type, admin)
    return RawJSONResponse(UserPointsNamesList.dump_json(user_points))


@ranking_members_router.get("/get/{rank_type}/", response_model=list[UserPointsNames])
async def member_classification(
    rank_type: str, dsrc: SourceDep, app_context: AppContext
) -> RawJSONResponse:
    return await get_classification(dsrc, app_context.rank_ctx, rank_type, False)


@old_router.get(
    "/members/classification/{rank_type}/", response_model=list[UserPointsNames]
)
async def member_classification_old(
    rank_type: str, dsrc: SourceDep, app_context: AppContext
) -> RawJSONResponse:
    return await member_classification(rank_type, dsrc, app_context)


@ranking_admin_router.get("/get/{rank_type}/", response_model=list[UserPointsNames])
async def member_classification_admin(
    rank_type: str, dsrc: SourceDep, app_context: AppContext
) -> RawJSONResponse:
    return await get_classification(dsrc, app_context.rank_ctx, rank_type, True)


@old_router.get(
    "/admin/classification/{rank_type}/", response_model=list[UserPointsNames]
)
async def member_classification_admin_old(
    rank_type: str, dsrc: SourceDep, app_context: AppContext
) -> RawJSONResponse:
    return await member_classification_admin(rank_type, dsrc, app_context)


@ranking_admin_router.post("/sync/")
async def sync_publish_classification(
    dsrc: SourceDep, app_context: AppContext, publish: Optional[str] = None
) -> None:
    do_publish = publish == "publish"
    await sync_publish_ranking(app_context.rank_ctx, dsrc, do_publish)


@ranking_admin_router.get("/events/user/{user_id}/", response_model=list[UserEvent])
async def get_user_events_in_class(
    user_id: str,
    dsrc: SourceDep,
    app_context: AppContext,
    class_id: Optional[int] = None,
    rank_type: Optional[str] = None,
) -> RawJSONResponse:
    try:
        user_events = await mod_user_events_in_class(
            dsrc, app_context.rank_ctx, user_id, class_id, rank_type
        )
    except AppError as e:
        raise ErrorResponse(400, e.err_type, e.err_desc, e.debug_key)

    return RawJSONResponse(UserEventsList.dump_json(user_events))


@ranking_admin_router.get("/events/all/", response_model=list[ClassEvent])
async def get_events_in_class(
    dsrc: SourceDep,
    app_context: AppContext,
    class_id: Optional[int] = None,
    rank_type: Optional[str] = None,
) -> RawJSONResponse:
    try:
        events = await mod_events_in_class(
            dsrc, app_context.rank_ctx, class_id, rank_type
        )
    except AppError as e:
        raise ErrorResponse(400, e.err_type, e.err_desc, e.debug_key)

    return RawJSONResponse(EventsList.dump_json(events))


@ranking_admin_router.get(
    "/users/event/{event_id}/", response_model=list[UserPointsNames]
)
async def get_event_users(
    event_id: str,
    dsrc: SourceDep,
    app_context: AppContext,
) -> RawJSONResponse:
    # Result could be empty!
    event_users = await ctxlize_wrap(get_event_user_points, conn_wrap)(
        app_context.rank_ctx, dsrc, event_id
    )

    return RawJSONResponse(UserPointsNamesList.dump_json(event_users))
