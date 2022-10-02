import logging
from urllib.parse import urlencode

import opaquepy as opq
from fastapi import APIRouter, Request, Security, BackgroundTasks

import apiserver.data as data
import apiserver.utilities as util
from apiserver.auth import authentication
from apiserver.auth.authentication import send_register_start
from apiserver.auth.header import auth_header
from apiserver.data import Source, NoDataError, DataError
from apiserver.define import (
    LOGGER_NAME,
    UpdatePasswordRequest,
    ChangePasswordRequest,
    credentials_url,
    ErrorResponse,
    UpdatePasswordFinish,
    UpdateEmail,
    UpdateEmailCheck,
    ChangedEmailResponse,
    UpdateEmailState,
)
from apiserver.env import Config
from apiserver.routers.helper import require_user

router = APIRouter()

logger = logging.getLogger(LOGGER_NAME)


def send_reset_email(
    background_tasks: BackgroundTasks, receiver: str, mail_pass: str, reset_link: str
):
    add_vars = {
        "reset_link": reset_link,
    }

    def send_lam():
        util.send_email(
            "passwordchange.html.jinja2",
            receiver,
            mail_pass,
            "Request for password reset",
            add_vars,
        )

    background_tasks.add_task(send_lam)


def send_change_email_email(
    background_tasks: BackgroundTasks,
    receiver: str,
    mail_pass: str,
    reset_link: str,
    old_email: str,
):
    add_vars = {
        "old_email": old_email,
        "reset_link": reset_link,
    }

    def send_lam():
        util.send_email(
            "emailchange.html.jinja2",
            receiver,
            mail_pass,
            "Please confirm your new email",
            add_vars,
        )

    background_tasks.add_task(send_lam)


@router.post("/update/password/reset/")
async def request_password_change(
    change_pass: ChangePasswordRequest,
    request: Request,
    background_tasks: BackgroundTasks,
):
    dsrc: Source = request.app.state.dsrc
    async with data.get_conn(dsrc) as conn:
        is_registered = await data.user.userdata_registered_by_email(
            dsrc, conn, change_pass.email
        )
    logger.debug(f"Reset requested - is_registered={is_registered}")
    flow_id = util.random_time_hash_hex()
    params = {"reset_id": flow_id, "email": change_pass.email}
    reset_url = f"{credentials_url}reset/?{urlencode(params)}"

    await data.kv.store_string(dsrc, change_pass.email, flow_id, 1000)

    config: Config = request.app.state.config
    if is_registered:
        send_reset_email(
            background_tasks, change_pass.email, config.MAIL_PASS, reset_url
        )


@router.post("/update/password/start/")
async def update_password_start(update_pass: UpdatePasswordRequest, request: Request):
    dsrc: Source = request.app.state.dsrc

    try:
        stored_flow_id = await data.kv.get_string(dsrc, update_pass.email)
    except NoDataError as e:
        logger.debug(e.message)
        reason = "No reset has been requested for this user."
        raise ErrorResponse(
            400, err_type="invalid_reset", err_desc=reason, debug_key="no_user_reset"
        )

    if stored_flow_id != update_pass.flow_id:
        reason = "No reset request matches this flow_id."
        logger.debug(reason)
        raise ErrorResponse(
            400, err_type="invalid_reset", err_desc=reason, debug_key="no_flow_reset"
        )

    async with data.get_conn(dsrc) as conn:
        u = await data.user.get_user_by_email(dsrc, conn, update_pass.email)

    return await send_register_start(dsrc, u.user_id, update_pass.client_request)


@router.post("/update/password/finish/")
async def update_password_finish(update_finish: UpdatePasswordFinish, request: Request):
    dsrc: Source = request.app.state.dsrc

    try:
        saved_state = await data.kv.get_register_state(dsrc, update_finish.auth_id)
    except NoDataError as e:
        logger.debug(e.message)
        reason = "Reset not initialized or expired."
        raise ErrorResponse(
            400, err_type="invalid_reset", err_desc=reason, debug_key="no_reset_start"
        )

    password_file = opq.register_finish(update_finish.client_request)

    async with data.get_conn(dsrc) as conn:
        await data.user.update_password_file(
            dsrc, conn, saved_state.user_id, password_file
        )

        await data.refreshtoken.delete_by_user_id(dsrc, conn, saved_state.user_id)


@router.post("/update/email/send/")
async def update_email(
    new_email: UpdateEmail,
    request: Request,
    background_tasks: BackgroundTasks,
    authorization: str = Security(auth_header),
):
    dsrc: Source = request.app.state.dsrc
    user_id = new_email.user_id
    await require_user(authorization, dsrc, user_id)

    try:
        async with data.get_conn(dsrc) as conn:
            u = await data.user.get_user_by_id(dsrc, conn, user_id)
    except NoDataError:
        return ErrorResponse(
            400, "bad_update", "User no longer exists.", "update_user_empty"
        )
    old_email = u.email

    flow_id = util.random_time_hash_hex(user_id)
    params = {
        "flow_id": flow_id,
        "user": old_email,
        "redirect": "client:account/email/",
    }
    reset_url = f"{credentials_url}?{urlencode(params)}"

    config: Config = request.app.state.config
    send_change_email_email(
        background_tasks, new_email.new_email, config.MAIL_PASS, reset_url, old_email
    )

    state = UpdateEmailState(
        old_email=old_email, new_email=new_email.new_email, user_id=user_id
    )

    await data.kv.store_update_email(dsrc, flow_id, state)
    await data.kv.store_string(dsrc, user_id, flow_id, 1000)


@router.post("/update/email/check/")
async def update_email_check(update_check: UpdateEmailCheck, request: Request):
    dsrc: Source = request.app.state.dsrc

    flow_user = await authentication.check_password(dsrc, update_check.code)

    try:
        stored_email = await data.kv.get_update_email(dsrc, update_check.flow_id)
    except NoDataError as e:
        reason = "Update request has expired, please try again!"
        logger.debug(reason + f" {flow_user.user_id}")
        return ErrorResponse(status_code=400, err_type="bad_update", err_desc=reason)
    user_id = stored_email.user_id

    async with data.get_conn(dsrc) as conn:
        await data.refreshtoken.delete_by_user_id(dsrc, conn, flow_user.user_id)

        count_ud = await data.user.update_user_email(
            dsrc, conn, user_id, stored_email.new_email
        )
        if count_ud != 1:
            raise DataError("Internal data error.", "user_data_error")

    return ChangedEmailResponse(
        old_email=stored_email.old_email, new_email=stored_email.new_email
    )
