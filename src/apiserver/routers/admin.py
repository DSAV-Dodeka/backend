import logging

from fastapi import APIRouter, Request
from sqlalchemy.ext.asyncio import AsyncConnection

from apiserver.define import LOGGER_NAME
from apiserver.define.entities import UserData, UserScopeData
from apiserver.define.reqres import ScopeAddRequest, ErrorResponse, ScopeRemoveRequest
from apiserver import data
from apiserver.data import Source, DataError, NoDataError
from apiserver.auth.header import Authorization
from apiserver.routers.helper import require_admin

router = APIRouter()

logger = logging.getLogger(LOGGER_NAME)


@router.get("/admin/users/", response_model=list[UserData])
async def get_users(request: Request, authorization: Authorization):
    dsrc: Source = request.state.dsrc
    await require_admin(authorization, dsrc)
    async with data.get_conn(dsrc) as conn:
        user_data = await data.user.get_all_userdata(dsrc, conn)
    return user_data


@router.get("/admin/scopes/all/", response_model=list[UserScopeData])
async def get_users_scopes(request: Request, authorization: Authorization):
    dsrc: Source = request.state.dsrc
    await require_admin(authorization, dsrc)
    async with data.get_conn(dsrc) as conn:
        user_scope_data = await data.user.get_all_users_scopes(dsrc, conn)
    return user_scope_data


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
            await data.user.add_scope(
                dsrc, conn, scope_request.user_id, scope_request.scope
            )
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
                dsrc, conn, scope_request.user_id, scope_request.scope
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
