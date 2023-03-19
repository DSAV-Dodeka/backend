import logging

from fastapi import APIRouter, Security, Request
from sqlalchemy.ext.asyncio import AsyncConnection

from apiserver.define import LOGGER_NAME
from apiserver.define.entities import UserData
from apiserver.define.reqres import ScopeAddRequest, ErrorResponse
import apiserver.data as data
from apiserver.data import Source, DataError, NoDataError
from apiserver.auth.header import auth_header
from apiserver.routers.helper import require_admin

router = APIRouter()

logger = logging.getLogger(LOGGER_NAME)


@router.get("/admin/users/", response_model=list[UserData])
async def get_users(request: Request, authorization: str = Security(auth_header)):
    dsrc: Source = request.app.state.dsrc
    await require_admin(authorization, dsrc)
    async with data.get_conn(dsrc) as conn:
        user_data = await data.user.get_all_userdata(dsrc, conn)
    return user_data


@router.post("/admin/scope/add/")
async def add_scope(
    scope_request: ScopeAddRequest,
    request: Request,
    authorization: str = Security(auth_header),
):
    dsrc: Source = request.app.state.dsrc
    await require_admin(authorization, dsrc)
    async with data.get_conn(dsrc) as conn:
        conn: AsyncConnection = conn
        try:
            await data.user.add_scope(
                dsrc, conn, scope_request.user_id, scope_request.scope
            )
        except NoDataError as e:
            logger.debug(e.message)
            raise ErrorResponse(
                400, err_type=f"invalid_scope_add", err_desc=e.message, debug_key=e.key
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
