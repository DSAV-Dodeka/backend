from typing import Annotated
from fastapi import Depends, Request
from apiserver.app.error import ErrorResponse
from apiserver.app.ops.header import auth_header, verify_token_header
from apiserver.data.context.app_context import Code, SourceContexts

from apiserver.data.source import Source
from apiserver.lib.model.entities import AccessToken
from apiserver.lib.resource.error import ResourceError, resource_error_code
from auth.data.context import Contexts as AuthContexts
from datacontext.context import ctxlize

# Due to some internal stuff in FastAPI/Starlette, it's important to make all dependencies async. https://github.com/tiangolo/fastapi/discussions/5999


async def dep_source(request: Request) -> Source:
    dsrc: Source = request.state.dsrc
    return dsrc


async def dep_app_context(request: Request) -> SourceContexts:
    cd: Code = request.state.cd
    return cd.app_context


async def dep_auth_context(request: Request) -> AuthContexts:
    cd: Code = request.state.cd
    return cd.auth_context


SourceDep = Annotated[Source, Depends(dep_source)]
AppContext = Annotated[SourceContexts, Depends(dep_app_context)]
AuthContext = Annotated[AuthContexts, Depends(dep_auth_context)]

Authorization = Annotated[str, Depends(auth_header)]


async def dep_header_token(
    authorization: Authorization, dsrc: SourceDep, app_ctx: AppContext
) -> AccessToken:
    try:
        return await ctxlize(verify_token_header)(
            app_ctx.authrz_ctx, authorization, dsrc
        )
    except ResourceError as e:
        code = resource_error_code(e.err_type)

        raise ErrorResponse(
            code,
            err_type=e.err_type,
            err_desc=e.err_desc,
            debug_key=e.debug_key,
        )


AccessDep = Annotated[AccessToken, Depends(dep_header_token)]


def verify_user(acc: AccessToken, user_id: str) -> bool:
    """Verifies if the user in the access token corresponds to the provided user_id.

    Args:
        acc: AccessToken object.
        user_id: user_id that will be compared against.

    Returns:
        True if user_id = acc.sub.

    Raises:
        ErrorResponse: If access token subject does not correspond to user_id.
    """
    if acc.sub != user_id:
        reason = "Resource not available to this subject."
        raise ErrorResponse(
            403, err_type="wrong_subject", err_desc=reason, debug_key="bad_sub"
        )

    return True


def has_scope(scopes: str, required: set[str]) -> bool:
    scope_set = set(scopes.split())
    return required.issubset(scope_set)


async def require_admin(acc: AccessDep) -> AccessToken:
    if not has_scope(acc.scope, {"admin"}):
        raise ErrorResponse(
            403,
            err_type="insufficient_scope",
            err_desc="Insufficient permissions to access this resource.",
            debug_key="low_perms",
        )

    return acc


async def require_member(acc: AccessDep) -> AccessToken:
    if not has_scope(acc.scope, {"member"}):
        raise ErrorResponse(
            403,
            err_type="insufficient_scope",
            err_desc="Insufficient permissions to access this resource.",
            debug_key="low_perms",
        )

    return acc


RequireMember = Annotated[AccessToken, Depends(require_member)]
RequireAdmin = Annotated[AccessToken, Depends(require_admin)]
