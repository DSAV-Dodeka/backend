from typing import Optional
from fastapi import APIRouter
from starlette.requests import Request

from apiserver.app.error import ErrorResponse, AppError
from apiserver.app.modules.ranking import (
    mod_events_in_class,
    mod_user_events_in_class,
)
from apiserver.app.ops.header import Authorization
from apiserver.app.response import RawJSONResponse
from apiserver.app.routers.helper import require_admin, require_member
from apiserver.data.api.classifications import get_event_user_points
from apiserver.data.context.app_context import Code, RankingContext, conn_wrap
from apiserver.data.context.authorize import require_admin as ctx_require_admin
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
from apiserver.data import Source
from datacontext.context import ctxlize

router = APIRouter()


@router.post("/admin/ranking/update/")
async def admin_update_ranking(
    new_event: NewEvent, request: Request, authorization: Authorization
) -> None:
    dsrc: Source = request.state.dsrc
    cd: Code = request.state.cd
    await require_admin(authorization, dsrc)

    try:
        await add_new_event(cd.app_context.rank_ctx, dsrc, new_event)
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


@router.get(
    "/members/classification/{rank_type}/", response_model=list[UserPointsNames]
)
async def member_classification(
    rank_type: str, request: Request, authorization: Authorization
) -> RawJSONResponse:
    dsrc: Source = request.state.dsrc
    cd: Code = request.state.cd
    await require_member(authorization, dsrc)

    return await get_classification(dsrc, cd.app_context.rank_ctx, rank_type, False)


@router.get("/admin/classification/{rank_type}/", response_model=list[UserPointsNames])
async def member_classification_admin(
    rank_type: str, request: Request, authorization: Authorization
) -> RawJSONResponse:
    dsrc: Source = request.state.dsrc
    cd: Code = request.state.cd
    await require_admin(authorization, dsrc)

    return await get_classification(dsrc, cd.app_context.rank_ctx, rank_type, True)


@router.post("/admin/class/sync/")
async def sync_publish_classification(
    request: Request, authorization: Authorization, publish: Optional[str] = None
) -> None:
    dsrc: Source = request.state.dsrc
    cd: Code = request.state.cd
    await require_admin(authorization, dsrc)

    do_publish = publish == "publish"
    await sync_publish_ranking(cd.app_context.rank_ctx, dsrc, do_publish)


@router.get("/admin/class/events/user/{user_id}/", response_model=list[UserEvent])
async def get_user_events_in_class(
    user_id: str,
    request: Request,
    authorization: Authorization,
    class_id: Optional[int] = None,
    rank_type: Optional[str] = None,
) -> RawJSONResponse:
    dsrc: Source = request.state.dsrc
    cd: Code = request.state.cd
    await require_admin(authorization, dsrc)

    try:
        user_events = await mod_user_events_in_class(
            dsrc, cd.app_context.rank_ctx, user_id, class_id, rank_type
        )
    except AppError as e:
        raise ErrorResponse(400, e.err_type, e.err_desc, e.debug_key)

    return RawJSONResponse(UserEventsList.dump_json(user_events))


@router.get("/admin/class/events/all/", response_model=list[ClassEvent])
async def get_events_in_class(
    request: Request,
    authorization: Authorization,
    class_id: Optional[int] = None,
    rank_type: Optional[str] = None,
) -> RawJSONResponse:
    dsrc: Source = request.state.dsrc
    cd: Code = request.state.cd
    await require_admin(authorization, dsrc)

    try:
        events = await mod_events_in_class(
            dsrc, cd.app_context.rank_ctx, class_id, rank_type
        )
    except AppError as e:
        raise ErrorResponse(400, e.err_type, e.err_desc, e.debug_key)

    return RawJSONResponse(EventsList.dump_json(events))


@router.get(
    "/admin/class/users/event/{event_id}/", response_model=list[UserPointsNames]
)
async def get_event_users(
    event_id: str, request: Request, authorization: Authorization
) -> RawJSONResponse:
    dsrc: Source = request.state.dsrc
    cd: Code = request.state.cd
    await ctx_require_admin(cd.app_context.authrz_ctx, authorization, dsrc)

    # Result could be empty!
    event_users = await ctxlize(get_event_user_points, conn_wrap)(
        cd.wrap, dsrc, event_id
    )

    return RawJSONResponse(UserPointsNamesList.dump_json(event_users))
