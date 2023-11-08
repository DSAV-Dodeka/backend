from apiserver.app.error import ErrorResponse
from apiserver.app.routers.helper.helper import handle_auth
from apiserver.data.context.app_context import AuthorizeAppContext
from apiserver.data.source import Source
from datacontext.context import ContextRegistry


ctx_reg = ContextRegistry()


@ctx_reg.register(AuthorizeAppContext)
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
