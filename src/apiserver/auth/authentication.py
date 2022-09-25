import logging

import opaquepy as opq

from apiserver.define import SavedRegisterState, PasswordResponse, LOGGER_NAME, ErrorResponse, FlowUser
import apiserver.utilities as util
import apiserver.data as data
from apiserver.data import Source, NoDataError
from apiserver.routers.helper import require_user

logger = logging.getLogger(LOGGER_NAME)


async def send_register_start(dsrc: Source, user_usph: str, client_request: str, user_id: int):
    """ Generates auth_id """
    auth_id = util.random_time_hash_hex(user_usph)

    async with data.get_conn(dsrc) as conn:
        opaque_setup = await data.opaquesetup.get_setup(dsrc, conn)

    response = opq.register(opaque_setup, client_request, user_usph)
    saved_state = SavedRegisterState(user_usph=user_usph, id=user_id)
    await data.kv.store_auth_register_state(dsrc, auth_id, saved_state)

    return PasswordResponse(server_message=response, auth_id=auth_id)


async def check_password(dsrc: Source, auth_code: str, authorization: str) -> FlowUser:
    try:
        flow_user = await data.kv.pop_flow_user(dsrc, auth_code)
    except NoDataError as e:
        logger.debug(e.message)
        reason = "Expired or missing auth code"
        raise ErrorResponse(400, err_type="invalid_check", err_desc=reason, debug_key="empty_flow")
    await require_user(authorization, dsrc, flow_user.user_usph)

    return flow_user
