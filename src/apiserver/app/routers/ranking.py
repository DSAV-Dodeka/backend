from starlette.requests import Request

from apiserver.app.error import ErrorResponse, AppError
from apiserver.app.modules.ranking import add_new_event, NewEvent
from apiserver.app.ops.header import Authorization
from apiserver.app.routers.admin import router
from apiserver.app.routers.helper import require_admin
from apiserver.data import Source


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
