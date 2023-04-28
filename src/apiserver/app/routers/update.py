import logging
from urllib.parse import urlencode

import opaquepy as opq
from fastapi import APIRouter, Request, BackgroundTasks

from apiserver import data
import apiserver.lib.utilities as util
from apiserver.app.error import ErrorResponse
from apiserver.app.ops.mail import send_email
from apiserver.app.routers.helper import authentication
from apiserver.app.routers.helper.authentication import send_register_start
from apiserver.app.ops.header import Authorization
from apiserver.data import Source, NoDataError, DataError
from apiserver.app.define import LOGGER_NAME, credentials_url
from apiserver.app.model.models import (
    UpdatePasswordRequest,
    ChangePasswordRequest,
    UpdatePasswordFinish,
    UpdateEmail,
    UpdateEmailCheck,
    ChangedEmailResponse,
    UpdateEmailState,
    DeleteAccount,
    DeleteAccountCheck,
    DeleteUrlResponse,
)
from apiserver.app.env import Config
from apiserver.app.routers.helper import require_user

router = APIRouter()

logger = logging.getLogger(LOGGER_NAME)


def send_reset_email(
    background_tasks: BackgroundTasks, receiver: str, mail_pass: str, reset_link: str
):
    add_vars = {
        "reset_link": reset_link,
    }

    def send_lam():
        send_email(
            logger,
            "passwordchange.jinja2",
            receiver,
            mail_pass,
            "Request for password reset",
            add_vars=add_vars,
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
        send_email(
            logger,
            "emailchange.jinja2",
            receiver,
            mail_pass,
            "Please confirm your new email",
            add_vars=add_vars,
        )

    background_tasks.add_task(send_lam)


@router.post("/update/password/reset/")
async def request_password_change(
    change_pass: ChangePasswordRequest,
    request: Request,
    background_tasks: BackgroundTasks,
):
    """Initiated from authpage. Sends out e-mail with reset link."""
    dsrc: Source = request.state.dsrc
    async with data.get_conn(dsrc) as conn:
        ud = await data.user.get_userdata_by_email(conn, change_pass.email)
    logger.debug(f"Reset requested - is_registered={ud.registered}")
    flow_id = util.random_time_hash_hex()
    params = {"reset_id": flow_id, "email": change_pass.email}
    reset_url = f"{credentials_url}reset/?{urlencode(params)}"

    await data.kv.store_string(dsrc, flow_id, change_pass.email, 1000)

    config: Config = request.state.config
    if ud.registered:
        send_reset_email(
            background_tasks, change_pass.email, config.MAIL_PASS, reset_url
        )


@router.post("/update/password/start/")
async def update_password_start(update_pass: UpdatePasswordRequest, request: Request):
    dsrc: Source = request.state.dsrc

    try:
        stored_email = await data.kv.pop_string(dsrc, update_pass.flow_id)
    except NoDataError as e:
        logger.debug(e.message)
        reason = "No reset has been requested for this user."
        raise ErrorResponse(
            400, err_type="invalid_reset", err_desc=reason, debug_key="no_user_reset"
        )

    if stored_email != update_pass.email:
        reason = "Emails do not match for this reset!"
        logger.debug(reason)
        raise ErrorResponse(
            400,
            err_type="invalid_reset",
            err_desc=reason,
            debug_key="reset_no_email_match",
        )

    async with data.get_conn(dsrc) as conn:
        u = await data.user.get_user_by_email(conn, update_pass.email)

    return await send_register_start(dsrc, u.user_id, update_pass.client_request)


@router.post("/update/password/finish/")
async def update_password_finish(update_finish: UpdatePasswordFinish, request: Request):
    dsrc: Source = request.state.dsrc

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
        await data.user.update_password_file(conn, saved_state.user_id, password_file)

        await data.refreshtoken.delete_by_user_id(conn, saved_state.user_id)


@router.post("/update/email/send/")
async def update_email(
    new_email: UpdateEmail,
    request: Request,
    background_tasks: BackgroundTasks,
    authorization: Authorization,
):
    dsrc: Source = request.state.dsrc
    user_id = new_email.user_id
    await require_user(authorization, dsrc, user_id)

    try:
        async with data.get_conn(dsrc) as conn:
            u = await data.user.get_user_by_id(conn, user_id)
    except NoDataError:
        raise ErrorResponse(
            400, "bad_update", "User no longer exists.", "update_user_empty"
        )
    old_email = u.email

    flow_id = util.random_time_hash_hex(user_id)
    params = {
        "flow_id": flow_id,
        "user": old_email,
        "redirect": "client:account/email/",
        "extra": new_email.new_email,
    }
    reset_url = f"{credentials_url}?{urlencode(params)}"

    config: Config = request.state.config
    send_change_email_email(
        background_tasks, new_email.new_email, config.MAIL_PASS, reset_url, old_email
    )

    state = UpdateEmailState(
        old_email=old_email, new_email=new_email.new_email, user_id=user_id
    )

    await data.kv.store_update_email(dsrc, flow_id, state)


@router.post("/update/email/check/")
async def update_email_check(update_check: UpdateEmailCheck, request: Request):
    dsrc: Source = request.state.dsrc

    flow_user = await authentication.check_password(dsrc, update_check.code)

    try:
        stored_email = await data.kv.get_update_email(dsrc, update_check.flow_id)
    except NoDataError:
        reason = "Update request has expired, please try again!"
        logger.debug(reason + f" {flow_user.user_id}")
        raise ErrorResponse(status_code=400, err_type="bad_update", err_desc=reason)
    user_id = stored_email.user_id

    async with data.get_conn(dsrc) as conn:
        await data.refreshtoken.delete_by_user_id(conn, flow_user.user_id)

        count_ud = await data.user.update_user_email(
            conn, user_id, stored_email.new_email
        )
        if count_ud != 1:
            raise DataError("Internal data error.", "user_data_error")

    return ChangedEmailResponse(
        old_email=stored_email.old_email, new_email=stored_email.new_email
    )


@router.post("/update/delete/url/")
async def delete_account(
    delete_acc: DeleteAccount,
    request: Request,
    authorization: Authorization,
):
    dsrc: Source = request.state.dsrc
    user_id = delete_acc.user_id
    await require_user(authorization, dsrc, user_id)

    try:
        async with data.get_conn(dsrc) as conn:
            ud = await data.user.get_userdata_by_id(conn, user_id)
    except NoDataError:
        raise ErrorResponse(
            400, "bad_update", "User no longer exists.", "update_user_empty"
        )
    if not ud.registered:
        raise ErrorResponse(
            status_code=400,
            err_type="bad_delete",
            err_desc="User not registered",
            debug_key="delete_not_registered",
        )

    flow_id = util.random_time_hash_hex(user_id)
    params = {
        "flow_id": flow_id,
        "user": ud.email,
        "redirect": "client:account/delete/",
    }
    delete_url = f"{credentials_url}?{urlencode(params)}"

    await data.kv.store_string(dsrc, flow_id, user_id, 1000)

    return DeleteUrlResponse(delete_url=delete_url)


@router.post("/update/delete/check/")
async def delete_account_check(delete_check: DeleteAccountCheck, request: Request):
    dsrc: Source = request.state.dsrc

    flow_user = await authentication.check_password(dsrc, delete_check.code)

    try:
        stored_user_id = await data.kv.pop_string(dsrc, delete_check.flow_id)
    except NoDataError:
        reason = "Delete request has expired, please try again!"
        logger.debug(reason + f" {flow_user.user_id}")
        raise ErrorResponse(status_code=400, err_type="bad_update", err_desc=reason)

    async with data.get_conn(dsrc) as conn:
        try:
            await data.user.delete_user(conn, stored_user_id)
            return DeleteAccount(user_id=stored_user_id)
        except NoDataError:
            reason = "User for delete request does not exist!"
            logger.debug(reason + f" {flow_user.user_id}")
            raise ErrorResponse(
                status_code=400,
                err_type="bad_update",
                err_desc="Delete request has expired, please try again!",
            )
