from dodekaserver.define import ErrorResponse
from dodekaserver.auth.header import handle_header, BadAuth
from dodekaserver.define.entities import AccessToken


async def handle_auth(authorization: str) -> AccessToken:
    try:
        return await handle_header(authorization)
    except BadAuth as e:
        raise ErrorResponse(e.status_code, err_type=e.err_type, err_desc=e.err_desc, debug_key=e.debug_key)


async def require_admin(authorization: str):
    acc = await handle_auth(authorization)
    scope_set = set(acc.scope.split())
    if 'admin' not in scope_set:
        raise ErrorResponse(403, err_type="insufficient_perms", err_desc="Insufficient permissions to access this "
                                                                         "resource.", debug_key="low_perms")
