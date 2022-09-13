from apiserver.define import ErrorResponse
from apiserver.define.entities import AccessToken
from apiserver.data import Source
from apiserver.auth.header import handle_header, BadAuth


async def handle_auth(authorization: str, dsrc: Source) -> AccessToken:
    try:
        return await handle_header(authorization, dsrc)
    except BadAuth as e:
        raise ErrorResponse(e.status_code, err_type=e.err_type, err_desc=e.err_desc, debug_key=e.debug_key)


async def require_admin(authorization: str, dsrc: Source):
    acc = await handle_auth(authorization, dsrc)
    scope_set = set(acc.scope.split())
    if 'admin' not in scope_set:
        raise ErrorResponse(403, err_type="insufficient_perms", err_desc="Insufficient permissions to access this "
                                                                         "resource.", debug_key="low_perms")
