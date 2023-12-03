from loguru import logger
from urllib.parse import urlencode

import opaquepy as opq
from fastapi import APIRouter, BackgroundTasks
from pydantic import BaseModel
from apiserver.app.dependencies import (
    AppContext,
    AuthContext,
    RequireMember,
    SourceDep,
    verify_user,
)
from apiserver.app.modules.update import verify_delete_account
from apiserver.data.api.ud.userdata import get_userdata_by_id
from apiserver.data.api.user import delete_user
from apiserver.data.context.app_context import conn_wrap
from auth.core.response import PasswordResponse

import auth.core.util
from apiserver import data
from apiserver.app.error import AppError, ErrorKeys, ErrorResponse
from apiserver.app.ops.mail import (
    send_change_email_email,
    send_reset_email,
    mail_from_config,
)
from apiserver.data import ops
from apiserver.data.context.update import store_email_flow_password_change
from apiserver.define import DEFINE
from apiserver.lib.model.entities import UpdateEmailState
from auth.data.authentication import pop_flow_user
from auth.modules.register import send_register_start
from auth.modules.update import change_password
from datacontext.context import ctxlize_wrap
from store.error import DataError, NoDataError

router = APIRouter(prefix="/update", tags=["update"])


class ChangePasswordRequest(BaseModel):
    email: str


@router.post("/password/reset/")
async def request_password_change(
    change_pass: ChangePasswordRequest,
    dsrc: SourceDep,
    app_context: AppContext,
    background_tasks: BackgroundTasks,
) -> None:
    """Initiated from authpage. Sends out e-mail with reset link. Does nothing if user does not exist or is not yet
    properly registered."""

    # Check if registered user exists and if they have finished registration
    # If yes, then we generate a random flow ID that can later be used to confirm the password change
    flow_id = await store_email_flow_password_change(
        app_context.update_ctx, dsrc, change_pass.email
    )

    if flow_id is None:
        logger.debug(
            f"Reset requested - email {change_pass.email} does not exist or not"
            " registered."
        )
        return

    params = {"reset_id": flow_id, "email": change_pass.email}
    reset_url = f"{DEFINE.credentials_url}reset/?{urlencode(params)}"

    logger.opt(ansi=True).debug(f"Creating password reset email with url <u><red>{reset_url}</red></u>")
    send_reset_email(
        background_tasks,
        change_pass.email,
        mail_from_config(dsrc.config),
        reset_url,
    )


class UpdatePasswordRequest(BaseModel):
    email: str
    flow_id: str
    client_request: str


@router.post("/password/start/")
async def update_password_start(
    update_pass: UpdatePasswordRequest, dsrc: SourceDep, auth_context: AuthContext
) -> PasswordResponse:
    stored_email = await data.trs.pop_string(dsrc, update_pass.flow_id)
    if stored_email is None:
        reason = f"Password reset of account {update_pass.email}: No reset has been requested for this user."
        raise ErrorResponse(
            400, err_type="invalid_reset", err_desc=reason, debug_key="no_user_reset"
        )

    if stored_email != update_pass.email:
        reason = "Emails do not match for this reset!"
        logger.debug(f"{reason}: {stored_email} != {update_pass.email}")
        raise ErrorResponse(
            400,
            err_type="invalid_reset",
            err_desc=reason,
            debug_key="reset_no_email_match",
        )

    try:
        async with data.get_conn(dsrc) as conn:
            u = await ops.user.get_user_by_email(conn, update_pass.email)
    except NoDataError:
        reason = "User no longer exists!"
        logger.debug(reason)
        raise ErrorResponse(
            400,
            err_type="invalid_reset",
            err_desc=reason,
            debug_key="reset_user_not_exists",
        )

    logger.debug(f"Initiating password reset for user {u.user_id} with email {update_pass.email}")
    return await send_register_start(
        dsrc.store, auth_context.register_ctx, u.user_id, update_pass.client_request
    )


class UpdatePasswordFinish(BaseModel):
    auth_id: str
    client_request: str


@router.post("/password/finish/")
async def update_password_finish(
    update_finish: UpdatePasswordFinish,
    dsrc: SourceDep,
) -> None:
    try:
        saved_state = await data.trs.reg.get_register_state(dsrc, update_finish.auth_id)
    except NoDataError as e:
        logger.debug(f"Reset {update_finish} does not exist: {e.message}")
        reason = "Reset not initialized or expired."
        raise ErrorResponse(
            400, err_type="invalid_reset", err_desc=reason, debug_key="no_reset_start"
        )

    password_file = opq.register_finish(update_finish.client_request)

    await change_password(
        dsrc.store, data.schema.OPS, password_file, saved_state.user_id
    )

    logger.debug(f"Changed password for {saved_state.user_id}")


class UpdateEmail(BaseModel):
    user_id: str
    new_email: str


@router.post("/email/send/")
async def update_email(
    new_email: UpdateEmail,
    dsrc: SourceDep,
    member: RequireMember,
    background_tasks: BackgroundTasks,
) -> None:
    user_id = new_email.user_id

    # THROWS ErrorResponse
    verify_user(member, user_id)

    try:
        async with data.get_conn(dsrc) as conn:
            u = await ops.user.get_user_by_id(conn, user_id)
    except NoDataError:
        message = f"User {user_id} updating email to {new_email.new_email} no longer exists."
        logger.debug(message)
        raise ErrorResponse(
            400, "bad_update", message, "update_user_empty"
        )
    old_email = u.email

    flow_id = auth.core.util.random_time_hash_hex(user_id)
    params = {
        "flow_id": flow_id,
        "user": old_email,
        "redirect": "client:account/email/",
        "extra": new_email.new_email,
    }
    reset_url = f"{DEFINE.credentials_url}?{urlencode(params)}"

    state = UpdateEmailState(
        flow_id=flow_id,
        old_email=old_email,
        new_email=new_email.new_email,
        user_id=user_id,
    )

    await data.trs.reg.store_update_email(dsrc, user_id, state)
    logger.debug(f"Stored user {user_id} email change from {old_email} to {new_email.new_email} with flow_id {flow_id}.")

    logger.opt(ansi=True).debug(f"Creating email change email with url <red><u>{reset_url}</u></red>")
    send_change_email_email(
        background_tasks,
        new_email.new_email,
        mail_from_config(dsrc.config),
        reset_url,
        old_email,
    )


class UpdateEmailCheck(BaseModel):
    flow_id: str
    code: str


class ChangedEmailResponse(BaseModel):
    old_email: str
    new_email: str


@router.post("/email/check/")
async def update_email_check(
    update_check: UpdateEmailCheck,
    dsrc: SourceDep,
    auth_context: AuthContext,
) -> ChangedEmailResponse:
    try:
        flow_user = await pop_flow_user(
            auth_context.login_ctx, dsrc.store, update_check.code
        )
    except NoDataError as e:
        logger.debug(f"No flow_user for code {update_check.code} with error {e.message}")
        reason = "Expired or missing auth code"
        raise ErrorResponse(
            status_code=400,
            err_type=ErrorKeys.CHECK,
            err_desc=reason,
            debug_key="empty_flow",
        )

    logger.debug(f"flow_user found for code {update_check.code}: {flow_user.user_id}")

    try:
        stored_email = await data.trs.reg.get_update_email(dsrc, flow_user.user_id)
    except NoDataError:
        reason = "Update request has expired, please try again!"
        logger.debug(reason + f" {flow_user.user_id}")
        raise ErrorResponse(
            status_code=400,
            err_type="bad_update",
            err_desc=reason,
            debug_key="update_flow_expired",
        )

    user_id = stored_email.user_id
    logger.debug(f"email change request found for flow_user: {stored_email}")
    # The flow ID is the proof that the person who get the email is requesting the change
    # The code proves the person has the password, the flow ID proves the person has the old email
    if stored_email.flow_id != update_check.flow_id:
        reason = "Update check code and update flow ID do not match!"
        logger.debug(f"{reason} code flow_id: {update_check.flow_id}")
        raise ErrorResponse(
            400,
            err_type="bad_update",
            err_desc=reason,
            debug_key="update_email_flow_not_equal",
        )

    async with data.get_conn(dsrc) as conn:
        try:
            u = await ops.user.get_user_by_id(conn, user_id)
        except NoDataError:
            reason = "User for update email no longer exists."
            logger.debug(reason)
            raise ErrorResponse(
                400,
                err_type="bad_update",
                err_desc=reason,
                debug_key="update_email_user_not_exists"
            )

        # If someone changed their email by now, we do not want it possible to happen again
        if stored_email.old_email != u.email:
            reason = "Old email and current email do not match!"
            raise ErrorResponse(
                400,
                err_type="bad_update",
                err_desc=reason,
                debug_key="update_email_email_not_equal",
            )

        # Refresh tokens are no longer valid
        await data.schema.OPS.refresh.delete_by_user_id(conn, flow_user.user_id)

        count_ud = await data.user.update_user_email(
            conn, user_id, stored_email.new_email
        )
        if count_ud != 1:
            raise DataError("Internal data error.", "user_data_error")
    logger.debug(f"User {user_id} successfully changed email from {stored_email.old_email} to {stored_email.new_email}.")

    return ChangedEmailResponse(
        old_email=stored_email.old_email, new_email=stored_email.new_email
    )


class DeleteAccount(BaseModel):
    user_id: str


class DeleteUrlResponse(BaseModel):
    delete_url: str


@router.post("/delete/url/")
async def delete_account(
    delete_acc: DeleteAccount,
    dsrc: SourceDep,
    member: RequireMember,
) -> DeleteUrlResponse:
    user_id = delete_acc.user_id

    # THROWS ErrorResponse
    verify_user(member, user_id)

    try:
        async with data.get_conn(dsrc) as conn:
            ud = await get_userdata_by_id(conn, user_id)
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

    # At this point we know the user is a valid user and is still registered.
    # Latter is important because access token might still be valid even after deletion.

    flow_id = auth.core.util.random_time_hash_hex(user_id)
    params = {
        "flow_id": flow_id,
        "user": ud.email,
        "redirect": "client:account/delete/",
    }
    # This URL is a special login URL that will redirect back to /delete/check/
    # They will have generated a valid auth_code using the standard login flow
    delete_url = f"{DEFINE.credentials_url}?{urlencode(params)}"

    # We store that this is a delete request, so that a normal auth code generated using normal login won't be enough
    # to achieve deletion
    await data.trs.store_string(dsrc, flow_id, user_id, 1000)

    return DeleteUrlResponse(delete_url=delete_url)


class DeleteAccountCheck(BaseModel):
    flow_id: str
    code: str


@router.post("/delete/check/")
async def delete_account_check(
    delete_check: DeleteAccountCheck,
    dsrc: SourceDep,
    auth_context: AuthContext,
    app_context: AppContext,
) -> DeleteAccount:
    try:
        delete_user_id = await verify_delete_account(
            delete_check.code,
            delete_check.flow_id,
            dsrc,
            app_context.update_ctx,
            auth_context.login_ctx,
        )
    except AppError as e:
        raise ErrorResponse(
            status_code=400,
            err_type=e.err_type,
            err_desc=e.err_desc,
            debug_key=e.debug_key,
        )

    try:
        await ctxlize_wrap(delete_user, conn_wrap)(
            app_context.update_ctx, dsrc, delete_user_id
        )
        return DeleteAccount(user_id=delete_user_id)
    except NoDataError:
        reason = "User for delete request no longer exists!"
        logger.debug(reason + f" {delete_user_id}")
        raise AppError(
            err_type=ErrorKeys.UPDATE,
            err_desc=reason,
        )
