import datetime
import logging

from fastapi import APIRouter, Request
from fastapi.responses import ORJSONResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncConnection

from apiserver.define import LOGGER_NAME
from apiserver.app.error import ErrorResponse
from apiserver.data.api.classifications import check_user_in_class
from apiserver.lib.model.entities import UserData, UserScopeData, UserID
from apiserver import data
from apiserver.data import Source, DataError, NoDataError
from apiserver.app.ops.header import Authorization
from apiserver.app.routers.helper import require_admin

router = APIRouter()

logger = logging.getLogger(LOGGER_NAME)


@router.get("/admin/users/", response_model=list[UserData])
async def get_users(request: Request, authorization: Authorization):
    dsrc: Source = request.state.dsrc
    await require_admin(authorization, dsrc)
    async with data.get_conn(dsrc) as conn:
        user_data = await data.user.get_all_userdata(conn)
    return ORJSONResponse([ud.model_dump() for ud in user_data])


@router.get("/admin/scopes/all/", response_model=list[UserScopeData])
async def get_users_scopes(request: Request, authorization: Authorization):
    dsrc: Source = request.state.dsrc
    await require_admin(authorization, dsrc)
    async with data.get_conn(dsrc) as conn:
        user_scope_data = await data.user.get_all_users_scopes(conn)
    return ORJSONResponse([usd.model_dump() for usd in user_scope_data])


class ScopeAddRequest(BaseModel):
    user_id: str
    scope: str


@router.post("/admin/scopes/add/")
async def add_scope(
    scope_request: ScopeAddRequest,
    request: Request,
    authorization: Authorization,
):
    dsrc: Source = request.state.dsrc
    await require_admin(authorization, dsrc)

    if "admin" in scope_request.scope or "member" in scope_request.scope:
        reason = "Cannot add fundamental roles of 'member' or 'admin'."
        raise ErrorResponse(
            400,
            err_type="invalid_scope_add",
            err_desc=reason,
            debug_key="scope_admin_member_add",
        )

    async with data.get_conn(dsrc) as conn:
        conn: AsyncConnection = conn
        try:
            await data.user.add_scope(conn, scope_request.user_id, scope_request.scope)
        except NoDataError as e:
            logger.debug(e.message)
            raise ErrorResponse(
                400, err_type="invalid_scope_add", err_desc=e.message, debug_key=e.key
            )
        except DataError as e:
            if e.key == "scope_duplicate":
                reason = "Scope already exists on user."
                debug_key = "scope_duplicate"
            else:
                reason = "DbError adding scope."
                debug_key = "scope_db_error"
            logger.debug(e.message)
            raise ErrorResponse(
                status_code=400,
                err_type="invalid_scope_add",
                err_desc=reason,
                debug_key=debug_key,
            )

    return {}


class ScopeRemoveRequest(BaseModel):
    user_id: str
    scope: str


@router.post("/admin/scopes/remove/")
async def remove_scope(
    scope_request: ScopeRemoveRequest,
    request: Request,
    authorization: Authorization,
):
    dsrc: Source = request.state.dsrc
    await require_admin(authorization, dsrc)

    if "admin" in scope_request.scope or "member" in scope_request.scope:
        reason = "Cannot remove fundamental roles of 'member' or 'admin'."
        raise ErrorResponse(
            400,
            err_type="invalid_scope_remove",
            err_desc=reason,
            debug_key="scope_admin_member_remove",
        )

    async with data.get_conn(dsrc) as conn:
        conn: AsyncConnection = conn
        try:
            await data.user.remove_scope(
                conn, scope_request.user_id, scope_request.scope
            )
        except NoDataError as e:
            logger.debug(e.message)
            raise ErrorResponse(
                400,
                err_type="invalid_scope_remove",
                err_desc=e.message,
                debug_key=e.key,
            )
        except DataError as e:
            if e.key == "scope_nonexistent":
                reason = "Scope does not exists on user."
                debug_key = "scope_nonexistent"
            else:
                reason = "DbError removing scope."
                debug_key = "scope_db_error"
            logger.debug(e.message)
            raise ErrorResponse(
                status_code=400,
                err_type="invalid_scope_remove",
                err_desc=reason,
                debug_key=debug_key,
            )

    return {}


@router.get("/admin/users/ids/", response_model=list[UserID])
async def get_user_ids(request: Request, authorization: Authorization):
    dsrc: Source = request.state.dsrc
    await require_admin(authorization, dsrc)
    async with data.get_conn(dsrc) as conn:
        user_ids = await data.user.get_all_user_ids(conn)
    return ORJSONResponse([u_id.model_dump() for u_id in user_ids])


@router.get("/admin/users/names/", response_model=list[UserID])
async def get_user_names(request: Request, authorization: Authorization):
    dsrc: Source = request.state.dsrc
    await require_admin(authorization, dsrc)
    async with data.get_conn(dsrc) as conn:
        user_names = await data.user.get_all_user_names(conn)
    return ORJSONResponse([u_n.model_dump() for u_n in user_names])


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

            is_in_database = await check_user_in_class(
                conn, user.user_id, update.classification_id
            )

            # Update or insert in database.

            # See if hidden_date has past.
            hidden_date = await data.classifications.get_hidden_date(
                conn, update.classification_id
            )

    return
