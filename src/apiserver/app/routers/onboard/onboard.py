import json
import logging
from datetime import date
from urllib.parse import urlencode

from anyio import sleep
from fastapi import APIRouter, BackgroundTasks, Request
from pydantic import BaseModel

from apiserver import data
from apiserver.app.error import ErrorResponse, AppError
from apiserver.app.modules.register import (
    RegisterRequest,
    check_register,
    FinishRequest,
    finalize_save_register,
)
from apiserver.app.ops.header import Authorization
from apiserver.app.ops.mail import (
    send_signup_email,
    send_register_email,
    mail_from_config,
)
from apiserver.app.routers.helper import require_admin
from apiserver.data import Source
from apiserver.data.frame import Code
from apiserver.define import (
    LOGGER_NAME,
    DEFINE,
    email_expiration,
)
from apiserver.lib.model.entities import SignedUp, Signup
from auth.core.response import PasswordResponse
from auth.core.util import enc_b64url, random_time_hash_hex
from auth.modules.register import send_register_start
from store.error import DataError, NoDataError

router = APIRouter()

logger = logging.getLogger(LOGGER_NAME)


class SignupRequest(BaseModel):
    firstname: str
    lastname: str
    email: str
    phone: str


@router.post("/onboard/signup/")
async def init_signup(
    signup: SignupRequest, request: Request, background_tasks: BackgroundTasks
):
    """Signup is initiated by leaving basic information. User is redirected to AV'40 page, where they will actually
    sign up. Board can see who has signed up this way. There might not be full correspondence between exact signup and
    what is provided to AV'40. So there is a manual check."""
    dsrc: Source = request.state.dsrc
    if not signup.email.islower():
        signup.email = signup.email.lower()

    async with data.get_conn(dsrc) as conn:
        u_ex = await data.user.user_exists(conn, signup.email)
        su_ex = await data.signedup.signedup_exists(conn, signup.email)

    do_send_email = not u_ex and not su_ex
    logger.debug(f"{signup.email} /onboard/signup - do_send_email {do_send_email}")

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


@router.post("/onboard/email/")
async def email_confirm(confirm_req: EmailConfirm, request: Request):
    dsrc: Source = request.state.dsrc

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
            await data.signedup.insert_su_row(conn, signed_up.model_dump())
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


@router.get("/onboard/get/", response_model=list[SignedUp])
async def get_signedup(request: Request, authorization: Authorization):
    dsrc: Source = request.state.dsrc
    await require_admin(authorization, dsrc)
    async with data.get_conn(dsrc) as conn:
        signed_up = await data.signedup.get_all_signedup(conn)
    return signed_up


class SignupConfirm(BaseModel):
    email: str
    av40id: int
    joined: date


@router.post("/onboard/confirm/")
async def confirm_join(
    signup: SignupConfirm,
    request: Request,
    background_tasks: BackgroundTasks,
    authorization: Authorization,
):
    """Board confirms data from AV`40 signup through admin tool."""
    dsrc: Source = request.state.dsrc
    await require_admin(authorization, dsrc)
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

    send_register_email(
        background_tasks, signup_email, mail_from_config(dsrc.config), registration_url
    )


@router.post("/onboard/register/", response_model=PasswordResponse)
async def start_register(register_start: RegisterRequest, request: Request):
    """First step of OPAQUE registration, requires username and client message generated in first client registration
    step."""
    dsrc: Source = request.state.dsrc
    cd: Code = request.state.cd

    try:
        user_id = await check_register(dsrc, cd.frame.register_frm, register_start)
    except AppError as e:
        raise ErrorResponse(
            400, err_type=e.err_type, err_desc=e.err_desc, debug_key=e.debug_key
        )

    return await send_register_start(
        dsrc.store, cd.context.register_ctx, user_id, register_start.client_request
    )


@router.post("/onboard/finish/")
async def finish_register(register_finish: FinishRequest, request: Request):
    """At this point, we have info saved under 'userdata', 'users' and short-term storage as SavedRegisterState. All
    this data must match up for there to be a successful registration."""
    dsrc: Source = request.state.dsrc
    cd: Code = request.state.cd

    try:
        await finalize_save_register(dsrc, cd.frame.register_frm, register_finish)
    except AppError as e:
        # logger.debug(e.message)
        raise ErrorResponse(
            400,
            err_type=e.err_type,
            err_desc=e.err_desc,
            debug_key=e.debug_key,
        )
