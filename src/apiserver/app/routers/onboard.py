import json
from loguru import logger
from datetime import date
from urllib.parse import urlencode

from anyio import sleep
from fastapi import APIRouter, BackgroundTasks
from pydantic import BaseModel

from apiserver import data
from apiserver.app.dependencies import AppContext, AuthContext, SourceDep
from apiserver.app.error import ErrorResponse, AppError
from apiserver.app.modules.register import (
    RegisterRequest,
    check_register,
    FinishRequest,
    finalize_save_register,
)
from apiserver.app.ops.mail import (
    send_signup_email,
    send_register_email,
    mail_from_config,
)
from apiserver.define import (
    DEFINE,
    email_expiration,
)
from apiserver.lib.model.entities import SignedUp, Signup
from auth.core.response import PasswordResponse
from auth.core.util import enc_b64url, random_time_hash_hex
from auth.modules.register import send_register_start
from store.db import lit_model
from store.error import DataError, NoDataError

router = APIRouter(prefix="/onboard", tags=["onboard"])
onboard_admin_router = APIRouter(prefix="/onboard", tags=["onboard"])


class SignupRequest(BaseModel):
    firstname: str
    lastname: str
    email: str
    phone: str


@router.post("/signup/")
async def init_signup(
    signup: SignupRequest, dsrc: SourceDep, background_tasks: BackgroundTasks
) -> None:
    """Signup is initiated by leaving basic information. User is redirected to AV'40 page, where they will actually
    sign up. Board can see who has signed up this way. There might not be full correspondence between exact signup and
    what is provided to AV'40. So there is a manual check."""
    if not signup.email.islower():
        signup.email = signup.email.lower()

    async with data.get_conn(dsrc) as conn:
        u_ex = await data.user.user_exists(conn, signup.email)
        su_ex = await data.signedup.signedup_exists(conn, signup.email)

    do_send_email = not u_ex and not su_ex
    logger.debug(f"{signup.email} not u_ex={u_ex} and not su_ex={su_ex} is {do_send_email}")

    confirm_id = random_time_hash_hex()

    await data.trs.reg.store_email_confirmation(
        dsrc,
        confirm_id,
        Signup(
            email=signup.email,
            phone=signup.phone,
            firstname=signup.firstname,
            lastname=signup.lastname,
        ),
        email_expiration,
    )

    params = {"confirm_id": confirm_id}
    confirmation_url = f"{DEFINE.credentials_url}email/?{urlencode(params)}"

    if do_send_email:
        logger.opt(ansi=True).debug(f"Creating email with confirmation url <u><red>{confirmation_url}</red></u>")
        send_signup_email(
            background_tasks,
            signup.email,
            f"{signup.firstname} {signup.lastname}",
            mail_from_config(dsrc.config),
            confirmation_url,
            DEFINE.signup_url,
        )
    else:
        # Prevent client enumeration
        await sleep(0.00002)


class EmailConfirm(BaseModel):
    confirm_id: str


@router.post("/email/")
async def email_confirm(confirm_req: EmailConfirm, dsrc: SourceDep) -> None:
    try:
        signup = await data.trs.reg.get_email_confirmation(dsrc, confirm_req.confirm_id)
    except NoDataError as e:
        logger.debug(e.message)
        reason = "Incorrect confirm ID or expired."
        raise ErrorResponse(
            400, err_type="invalid_signup", err_desc=reason, debug_key="bad_confirm_id"
        )

    signed_up = SignedUp(
        firstname=signup.firstname,
        lastname=signup.lastname,
        email=signup.email,
        phone=signup.phone,
    )

    try:
        async with data.get_conn(dsrc) as conn:
            await data.signedup.insert_su_row(conn, lit_model(signed_up))
    except DataError as e:
        if e.key == "integrity_violation":
            logger.debug(e.key)
            raise ErrorResponse(
                400,
                err_type="invalid_signup",
                err_desc="Email already exists!",
                debug_key="user_exists",
            )
        else:
            logger.debug(e.message)
            raise e

    logger.debug(f"{signup.firstname} {signup.lastname} confirmed email {signup.email}")


@router.post("/register/", response_model=PasswordResponse)
async def start_register(
    register_start: RegisterRequest,
    dsrc: SourceDep,
    app_context: AppContext,
    auth_context: AuthContext,
) -> PasswordResponse:
    """First step of OPAQUE registration, requires username and client message generated in first client registration
    step."""
    try:
        user_id = await check_register(dsrc, app_context.register_ctx, register_start)
    except AppError as e:
        logger.debug(e)
        raise ErrorResponse(
            400, err_type=e.err_type, err_desc=e.err_desc, debug_key=e.debug_key
        )

    return await send_register_start(
        dsrc.store, auth_context.register_ctx, user_id, register_start.client_request
    )


@router.post("/finish/")
async def finish_register(
    register_finish: FinishRequest, dsrc: SourceDep, app_context: AppContext
) -> None:
    """At this point, we have info saved under 'userdata', 'users' and short-term storage as SavedRegisterState. All
    this data must match up for there to be a successful registration."""

    try:
        await finalize_save_register(dsrc, app_context.register_ctx, register_finish)
    except AppError as e:
        logger.debug(e.err_desc)
        raise ErrorResponse(
            400,
            err_type=e.err_type,
            err_desc=e.err_desc,
            debug_key=e.debug_key,
        )


@onboard_admin_router.get("/get/", response_model=list[SignedUp])
async def get_signedup(dsrc: SourceDep) -> list[SignedUp]:
    async with data.get_conn(dsrc) as conn:
        signed_up = await data.signedup.get_all_signedup(conn)
    return signed_up


@router.get("/get/", response_model=list[SignedUp])
async def get_signedup_old(dsrc: SourceDep) -> list[SignedUp]:
    return await get_signedup(dsrc)


class SignupConfirm(BaseModel):
    email: str
    av40id: int
    joined: date


@onboard_admin_router.post("/confirm/")
async def confirm_join(
    dsrc: SourceDep,
    signup: SignupConfirm,
    background_tasks: BackgroundTasks,
) -> None:
    """Board confirms data from AV`40 signup through admin tool."""
    signup_email = signup.email.lower()

    try:
        async with data.get_conn(dsrc) as conn:
            signed_up = await data.signedup.get_signedup_by_email(conn, signup_email)
    except DataError as e:
        if e.key == "signedup_empty":
            logger.debug(e.key)
            raise ErrorResponse(
                400,
                err_type="invalid_onboard",
                err_desc="No user under this e-mail in signup!",
                debug_key="no_user_signup",
            )
        else:
            logger.debug(e.message)
            raise e

    # Success here means removing any existing records in signedup and also the KV relating to that email

    register_id = random_time_hash_hex(short=True)
    async with data.get_conn(dsrc) as conn:
        await data.user.new_user(
            conn,
            signed_up,
            register_id,
            av40id=signup.av40id,
            joined=signup.joined,
        )
        await data.signedup.confirm_signup(conn, signup_email)

    logger.debug(f"Confirmed onboard for {signup_email} = {signed_up.firstname} {signed_up.lastname}")
    info = {
        "register_id": register_id,
        "firstname": signed_up.firstname,
        "lastname": signed_up.lastname,
        "email": signed_up.email,
        "phone": signed_up.phone,
    }
    info_str = enc_b64url(json.dumps(info).encode("utf-8"))
    params = {"info": info_str}
    registration_url = f"{DEFINE.credentials_url}register/?{urlencode(params)}"

    logger.opt(ansi=True).debug(f"Creating email with registration url <u><red>{registration_url}</red></u>")
    send_register_email(
        background_tasks, signup_email, mail_from_config(dsrc.config), registration_url
    )


@router.post("/confirm/")
async def confirm_join_old(
    dsrc: SourceDep,
    signup: SignupConfirm,
    background_tasks: BackgroundTasks,
) -> None:
    return await confirm_join(dsrc, signup, background_tasks)
