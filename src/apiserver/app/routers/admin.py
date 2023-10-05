import logging

from fastapi import APIRouter, Request
from fastapi.responses import ORJSONResponse
from pydantic import BaseModel

import apiserver.data.api.scope
import apiserver.data.api.ud.userdata
from apiserver import data
from apiserver.app.error import ErrorResponse
from apiserver.app.ops.header import Authorization
from apiserver.app.routers.helper import require_admin
from apiserver.data import Source
from apiserver.define import LOGGER_NAME
from apiserver.lib.model.entities import UserData, UserScopeData, UserID
from store.error import DataError, NoDataError

router = APIRouter()

logger = logging.getLogger(LOGGER_NAME)


@router.get("/admin/users/", response_model=list[UserData])
async def get_users(request: Request, authorization: Authorization):
    dsrc: Source = request.state.dsrc
    await require_admin(authorization, dsrc)
    async with data.get_conn(dsrc) as conn:
        user_data = await data.ud.get_all_userdata(conn)
    return ORJSONResponse([ud.model_dump() for ud in user_data])


@router.get("/admin/scopes/all/", response_model=list[UserScopeData])
async def get_users_scopes(request: Request, authorization: Authorization):
    dsrc: Source = request.state.dsrc
    await require_admin(authorization, dsrc)
    async with data.get_conn(dsrc) as conn:
        user_scope_data = await apiserver.data.api.scope.get_all_users_scopes(conn)
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
        try:
            await data.scope.add_scope(conn, scope_request.user_id, scope_request.scope)
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
        try:
            await data.scope.remove_scope(
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
        user_names = await data.ud.get_all_usernames(conn)
    return ORJSONResponse([u_n.model_dump() for u_n in user_names])
