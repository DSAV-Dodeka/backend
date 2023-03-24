import logging

import opaquepy as opq

from apiserver.define import (
    SavedRegisterState,
    PasswordResponse,
    LOGGER_NAME,
    ErrorResponse,
    FlowUser,
)
import apiserver.utilities as util
from apiserver import data
from apiserver.data import Source, NoDataError
from apiserver.routers.helper import require_user

logger = logging.getLogger(LOGGER_NAME)


async def send_register_start(dsrc: Source, user_id: str, client_request: str):
    """Generates auth_id"""
    auth_id = util.random_time_hash_hex(user_id)

    async with data.get_conn(dsrc) as conn:
        opaque_setup = await data.opaquesetup.get_setup(conn)

    response = opq.register(opaque_setup, client_request, user_id)
    saved_state = SavedRegisterState(user_id=user_id)
    await data.kv.store_auth_register_state(dsrc, auth_id, saved_state)

    return PasswordResponse(server_message=response, auth_id=auth_id)


async def check_password(
    dsrc: Source, auth_code: str, authorization: str = None
) -> FlowUser:
    try:
        flow_user = await data.kv.pop_flow_user(dsrc, auth_code)
    except NoDataError as e:
        logger.debug(e.message)
        reason = "Expired or missing auth code"
        raise ErrorResponse(
            400, err_type="invalid_check", err_desc=reason, debug_key="empty_flow"
        )
    if authorization is not None:
        await require_user(authorization, dsrc, flow_user.user_id)

    return flow_user
