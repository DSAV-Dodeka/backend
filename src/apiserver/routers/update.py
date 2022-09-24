import logging
from urllib.parse import urlencode

import opaquepy as opq

from fastapi import APIRouter, Request, Security, BackgroundTasks

from apiserver.define import LOGGER_NAME, FinishRequest, UpdatePasswordRequest, ChangePasswordRequest, credentials_url, \
    ErrorResponse, SavedRegisterState, UpdatePasswordFinish
import apiserver.utilities as util
from apiserver.define.entities import User
from apiserver.emailfn import send_email
import apiserver.data as data
from apiserver.data import Source, NoDataError, DataError
from apiserver.auth.authentication import send_register_start
from apiserver.auth.header import auth_header
from apiserver.env import Config
from apiserver.routers.helper import require_user

router = APIRouter()

logger = logging.getLogger(LOGGER_NAME)


def send_reset_email(background_tasks: BackgroundTasks, receiver: str, mail_pass: str, reset_link: str):
    add_vars = {
        "reset_link": reset_link,
    }

    def send_lam():
        send_email("passwordchange.html.jinja2", receiver, mail_pass, "Request for password reset", add_vars)

    background_tasks.add_task(send_lam)


@router.post("/update/password/reset/")
async def request_password_change(change_pass: ChangePasswordRequest, request: Request,
                                  background_tasks: BackgroundTasks):
    dsrc: Source = request.app.state.dsrc
    async with data.get_conn(dsrc) as conn:
        is_registered = await data.user.userdata_registered_by_email(dsrc, conn, change_pass.email)

    flow_id = util.random_time_hash_hex()
    params = {
        "reset_id": flow_id,
        "email": change_pass.email
    }
    reset_url = f"{credentials_url}reset/?{urlencode(params)}"

    await data.kv.store_string(dsrc, change_pass.email, flow_id, 1000)

    config: Config = request.app.state.config
    if is_registered:
        send_reset_email(background_tasks, change_pass.email, config.MAIL_PASS, reset_url)


@router.post("/update/password/start/")
async def update_password_start(update_pass: UpdatePasswordRequest, request: Request):
    dsrc: Source = request.app.state.dsrc

    try:
        stored_flow_id = await data.kv.get_string(dsrc, update_pass.email)
    except NoDataError as e:
        logger.debug(e.message)
        reason = "No reset has been requested for this user."
        raise ErrorResponse(400, err_type="invalid_reset", err_desc=reason, debug_key="no_user_reset")

    if stored_flow_id != update_pass.flow_id:
        reason = "No reset request matches this flow_id."
        logger.debug(reason)
        raise ErrorResponse(400, err_type="invalid_reset", err_desc=reason, debug_key="no_flow_reset")

    update_usph = util.usp_hex(update_pass.email)

    u = await data.user.get_user_by_usph(dsrc, update_usph)

    return await send_register_start(dsrc, update_usph, update_pass.client_request, u.id)


@router.post("/update/password/finish/")
async def update_password_finish(update_finish: UpdatePasswordFinish, request: Request):
    dsrc: Source = request.app.state.dsrc

    try:
        saved_state = await data.kv.get_register_state(dsrc, update_finish.auth_id)
    except NoDataError as e:
        logger.debug(e.message)
        reason = "Reset not initialized or expired."
        raise ErrorResponse(400, err_type="invalid_reset", err_desc=reason, debug_key="no_reset_start")

    password_file = opq.register_finish(update_finish.client_request)

    new_user = User(id=saved_state.id, usp_hex=saved_state.user_usph, password_file=password_file)

    await data.user.upsert_user(dsrc, new_user)



