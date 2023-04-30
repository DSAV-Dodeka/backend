import json
import logging
from datetime import date
from urllib.parse import urlencode

import opaquepy as opq
from anyio import sleep
from fastapi import APIRouter, BackgroundTasks, Request
from pydantic import BaseModel

import apiserver.lib.utilities as util
from apiserver import data
from apiserver.app.define import (
    LOGGER_NAME,
    signup_url,
    credentials_url,
    email_expiration,
)
from apiserver.app.env import Config
from apiserver.app.error import ErrorResponse
from apiserver.app.model.models import PasswordResponse
from apiserver.app.ops.header import Authorization
from apiserver.app.routers.helper import require_admin
from apiserver.app.routers.helper.authentication import send_register_start
from apiserver.app.ops.mail import (
    send_signup_email,
    send_register_email,
)
from apiserver.data import DataError, Source, NoDataError
from apiserver.lib.model.entities import SignedUp, Signup

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

    confirm_id = util.random_time_hash_hex()

    await data.trs.reg.store_email_confirmation(
        dsrc, confirm_id, Signup.parse_obj(signup), email_expiration
    )
    config: Config = request.state.config

    params = {"confirm_id": confirm_id}
    confirmation_url = f"{credentials_url}email/?{urlencode(params)}"

    if do_send_email:
        send_signup_email(
            background_tasks,
            signup.email,
            f"{signup.firstname} {signup.lastname}",
            config.MAIL_PASS,
            confirmation_url,
            signup_url,
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
            await data.signedup.insert_su_row(conn, signed_up.dict())
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

    register_id = util.random_time_hash_hex(short=True)
    async with data.get_conn(dsrc) as conn:
        await data.user.new_user(
            dsrc,
            conn,
            signed_up,
            register_id,
            av40id=signup.av40id,
            joined=signup.joined,
        )
        await data.signedup.confirm_signup(conn, signup_email)

    config: Config = request.state.config

    info = {
        "register_id": register_id,
        "firstname": signed_up.firstname,
        "lastname": signed_up.lastname,
        "email": signed_up.email,
        "phone": signed_up.phone,
    }
    info_str = util.enc_b64url(json.dumps(info).encode("utf-8"))
    params = {"info": info_str}
    registration_url = f"{credentials_url}register/?{urlencode(params)}"

    send_register_email(
        background_tasks, signup_email, config.MAIL_PASS, registration_url
    )


class RegisterRequest(BaseModel):
    email: str
    client_request: str
    register_id: str


@router.post("/onboard/register/", response_model=PasswordResponse)
async def start_register(register_start: RegisterRequest, request: Request):
    """First step of OPAQUE registration, requires username and client message generated in first client registration
    step."""
    dsrc: Source = request.state.dsrc
    try:
        async with data.get_conn(dsrc) as conn:
            ud = await data.user.get_userdata_by_register_id(
                conn, register_start.register_id
            )
    except NoDataError as e:
        logger.debug(e)
        reason = "No registration for that register_id"
        raise ErrorResponse(
            400,
            err_type="invalid_register",
            err_desc=reason,
            debug_key="no_register_for_id",
        )

    try:
        async with data.get_conn(dsrc) as conn:
            u = await data.user.get_user_by_id(conn, ud.user_id)
    except DataError as e:
        logger.debug(e)
        reason = "No registration for that user"
        raise ErrorResponse(
            400,
            err_type="invalid_register",
            err_desc=reason,
            debug_key="no_register_for_user",
        )

    if ud.registered or len(u.password_file) > 0:
        logger.debug("Already registered.")
        reason = "Bad registration."
        raise ErrorResponse(
            400,
            err_type="invalid_register",
            err_desc=reason,
            debug_key="bad_registration_start",
        )

    if u.email != register_start.email.lower():
        logger.debug("Registration start does not match e-mail")
        reason = "Bad registration."
        raise ErrorResponse(
            400,
            err_type="invalid_register",
            err_desc=reason,
            debug_key="bad_registration_start",
        )

    return await send_register_start(dsrc, ud.user_id, register_start.client_request)


class FinishRequest(BaseModel):
    auth_id: str
    email: str
    client_request: str
    register_id: str
    callname: str
    eduinstitution: str
    birthdate: date
    age_privacy: bool


@router.post("/onboard/finish/")
async def finish_register(register_finish: FinishRequest, request: Request):
    """At this point, we have info saved under 'userdata', 'users' and short-term storage as SavedRegisterState. All
    this data must match up for there to be a successful registration."""
    dsrc: Source = request.state.dsrc
    try:
        saved_state = await data.trs.reg.get_register_state(
            dsrc, register_finish.auth_id
        )
    except NoDataError as e:
        logger.debug(e.message)
        reason = "Registration not initialized or expired."
        raise ErrorResponse(
            400,
            err_type="invalid_registration",
            err_desc=reason,
            debug_key="no_register_start",
        )

    # Generate password file
    # Note that this is equal to the client request, it simply is a check for correct format
    try:
        password_file = opq.register_finish(register_finish.client_request)
    except ValueError as e:
        logger.debug(f"OPAQUE failure from client OPAQUE message: {str(e)}")
        raise ErrorResponse(
            400,
            err_type="invalid_registration",
            err_desc="Invalid OPAQUE registration.",
            debug_key="bad_opaque_registration",
        )

    try:
        async with data.get_conn(dsrc) as conn:
            ud = await data.user.get_userdata_by_register_id(
                conn, register_finish.register_id
            )
    except NoDataError as e:
        logger.debug(e)
        reason = "No registration for that register_id."
        raise ErrorResponse(
            400,
            err_type="invalid_register",
            err_desc=reason,
            debug_key="no_register_for_id",
        )

    if ud.registered:
        logger.debug("Already registered.")
        reason = "Bad registration."
        raise ErrorResponse(
            400,
            err_type="invalid_register",
            err_desc=reason,
            debug_key="bad_registration",
        )

    if ud.email != register_finish.email.lower():
        logger.debug("Registration does not match e-mail.")
        reason = "Bad registration."
        raise ErrorResponse(
            400,
            err_type="invalid_register",
            err_desc=reason,
            debug_key="bad_registration",
        )

    new_userdata = data.user.finished_userdata(
        ud,
        register_finish.callname,
        register_finish.eduinstitution,
        register_finish.birthdate,
        register_finish.age_privacy,
    )

    async with data.get_conn(dsrc) as conn:
        await data.user.update_password_file(conn, saved_state.user_id, password_file)
        await data.user.upsert_userdata(conn, new_userdata)
        await data.signedup.delete_signedup(conn, ud.email)

    # send welcome email
