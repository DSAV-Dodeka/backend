import logging

from apiserver.app.define import LOGGER_NAME
from apiserver.app.error import ErrorResponse
from apiserver.lib.model.entities import AccessToken
from apiserver.app.ops.header import handle_header, BadAuth
from apiserver.data import Source

logger = logging.getLogger(LOGGER_NAME)


async def handle_auth(authorization: str, dsrc: Source) -> AccessToken:
    try:
        return await handle_header(authorization, dsrc)
    except BadAuth as e:
        raise ErrorResponse(
            401,
            err_type=e.err_type,
            err_desc=e.err_desc,
            debug_key=e.debug_key,
        )


async def require_admin(authorization: str, dsrc: Source) -> bool:
    acc = await handle_auth(authorization, dsrc)
    scope_set = set(acc.scope.split())
    if "admin" not in scope_set:
        raise ErrorResponse(
            403,
            err_type="insufficient_perms",
            err_desc="Insufficient permissions to access this resource.",
            debug_key="low_perms",
        )
    else:
        return True


async def require_user(authorization: str, dsrc: Source, username: str) -> AccessToken:
    acc = await handle_auth(authorization, dsrc)
    if acc.sub != username:
        reason = "Resource not available to this subject."
        logger.debug(reason + f"- {username}")
        raise ErrorResponse(
            403, err_type="wrong_subject", err_desc=reason, debug_key="bad_sub"
        )
    else:
        return acc


async def require_member(authorization: str, dsrc: Source) -> bool:
    acc = await handle_auth(authorization, dsrc)
    scope_set = set(acc.scope.split())
    if "member" not in scope_set:
        raise ErrorResponse(
            403,
            err_type="insufficient_perms",
            err_desc="Insufficient permissions to access this resource.",
            debug_key="low_perms",
        )
    else:
        return True
