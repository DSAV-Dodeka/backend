from fastapi import APIRouter
from starlette.requests import Request

from apiserver import data
from apiserver.app.error import ErrorResponse, AppError
from apiserver.app.modules.ranking import add_new_event, NewEvent
from apiserver.app.ops.header import Authorization
from apiserver.app.response import RawJSONResponse
from apiserver.app.routers.helper import require_admin, require_member
from apiserver.data import Source
from apiserver.lib.model.entities import UserPointsNamesList

router = APIRouter()


@router.post("/admin/ranking/update/")
async def admin_update_ranking(
    new_event: NewEvent, request: Request, authorization: Authorization
):
    dsrc: Source = request.state.dsrc
    await require_admin(authorization, dsrc)

    try:
        await add_new_event(dsrc, new_event)
    except AppError as e:
        raise ErrorResponse(400, "invalid_ranking_update", e.err_desc, e.debug_key)


async def get_classification(dsrc: Source, rank_type, admin: bool = False):
    if rank_type not in {"training", "points"}:
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


@router.get("/members/classification/{rank_type}")
async def member_classification(
    rank_type, request: Request, authorization: Authorization
):
    dsrc: Source = request.state.dsrc
    await require_member(authorization, dsrc)

    return await get_classification(dsrc, rank_type, False)


@router.get("/admin/classification/{rank_type}")
async def member_classification_admin(
    rank_type, request: Request, authorization: Authorization
):
    dsrc: Source = request.state.dsrc
    await require_admin(authorization, dsrc)

    return await get_classification(dsrc, rank_type, True)
