import logging

from apiserver.app.error import ErrorResponse
from apiserver.app.routers.helper.helper import require_user
from apiserver.data import Source
from auth.data.authentication import pop_flow_user
from auth.data.context import LoginContext
from store.error import NoDataError
from apiserver.define import LOGGER_NAME
from auth.core.model import FlowUser

logger = logging.getLogger(LOGGER_NAME)


async def check_password(
    dsrc: Source,
    auth_code: str,
    context: LoginContext,
    authorization: str | None = None,
) -> FlowUser:
    try:
        flow_user = await pop_flow_user(context, dsrc.store, auth_code)
    except NoDataError as e:
        logger.debug(e.message)
        reason = "Expired or missing auth code"
        raise ErrorResponse(
            400, err_type="invalid_check", err_desc=reason, debug_key="empty_flow"
        )
    if authorization is not None:
        await require_user(authorization, dsrc, flow_user.user_id)

    return flow_user
