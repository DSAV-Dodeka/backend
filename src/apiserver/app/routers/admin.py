from loguru import logger

from fastapi import APIRouter, Depends
from fastapi.responses import ORJSONResponse
from pydantic import BaseModel
from apiserver.app.dependencies import SourceDep, require_admin

import apiserver.data.api.scope
import apiserver.data.api.ud.userdata
from apiserver import data
from apiserver.app.error import ErrorResponse
from apiserver.lib.model.entities import UserData, UserScopeData, UserID
from store.error import DataError, NoDataError

admin_router = APIRouter(
    prefix="/admin", tags=["admin"], dependencies=[Depends(require_admin)]
)


@admin_router.get("/users/", response_model=list[UserData])
async def get_users(dsrc: SourceDep) -> ORJSONResponse:
    async with data.get_conn(dsrc) as conn:
        user_data = await data.ud.get_all_userdata(conn)
    return ORJSONResponse([ud.model_dump() for ud in user_data])


@admin_router.get("/scopes/all/", response_model=list[UserScopeData])
async def get_users_scopes(dsrc: SourceDep) -> ORJSONResponse:
    async with data.get_conn(dsrc) as conn:
        user_scope_data = await apiserver.data.api.scope.get_all_users_scopes(conn)
    return ORJSONResponse([usd.model_dump() for usd in user_scope_data])


class ScopeAddRequest(BaseModel):
    user_id: str
    scope: str


@admin_router.post("/scopes/add/")
async def add_scope(scope_request: ScopeAddRequest, dsrc: SourceDep) -> None:
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


class ScopeRemoveRequest(BaseModel):
    user_id: str
    scope: str


@admin_router.post("/scopes/remove/")
async def remove_scope(scope_request: ScopeRemoveRequest, dsrc: SourceDep) -> None:
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


@admin_router.get("/users/ids/", response_model=list[UserID])
async def get_user_ids(dsrc: SourceDep) -> ORJSONResponse:
    async with data.get_conn(dsrc) as conn:
        user_ids = await data.user.get_all_user_ids(conn)
    return ORJSONResponse([u_id.model_dump() for u_id in user_ids])


@admin_router.get("/users/names/", response_model=list[UserID])
async def get_user_names(dsrc: SourceDep) -> ORJSONResponse:
    async with data.get_conn(dsrc) as conn:
        user_names = await data.ud.get_all_usernames(conn)
    return ORJSONResponse([u_n.model_dump() for u_n in user_names])
