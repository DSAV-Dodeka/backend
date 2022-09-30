import json

import logging
from urllib.parse import urlencode

from anyio import sleep
from fastapi import APIRouter, Security, BackgroundTasks, Request

import opaquepy as opq

from apiserver.define import ErrorResponse, LOGGER_NAME, signup_url, credentials_url, loc_dict
from apiserver.define.entities import SignedUp, UserData, User
from apiserver.define.reqres import SignupRequest, SignupConfirm, PasswordResponse, \
    RegisterRequest, FinishRequest, EmailConfirm, SavedRegisterState
import apiserver.utilities as util
import apiserver.data as data
from apiserver.data import DataError, Source, NoDataError
from apiserver.auth.header import auth_header
from apiserver.auth.authentication import send_register_start
from apiserver.env import Config
from apiserver.routers.helper import require_admin

router = APIRouter()

logger = logging.getLogger(LOGGER_NAME)


def send_signup_email(background_tasks: BackgroundTasks, receiver: str, mail_pass: str, redirect_link: str,
                      signup_link: str):
    add_vars = {
        "redirect_link": redirect_link,
        "signup_link": signup_link
    }

    def send_lam():
        util.send_email("confirm.html.jinja2", receiver, mail_pass, "Please confirm your email", add_vars)

    background_tasks.add_task(send_lam)


def send_register_email(background_tasks: BackgroundTasks, receiver: str, mail_pass: str, register_link: str):
    add_vars = {
        "register_link": register_link
    }

    def send_lam():
        org_name = loc_dict['loc']['org_name']
        util.send_email("register.html.jinja2", receiver, mail_pass, f"Welcome to {org_name}", add_vars)

    background_tasks.add_task(send_lam)


@router.post("/onboard/signup/")
async def init_signup(signup: SignupRequest, request: Request, background_tasks: BackgroundTasks):
    """ Signup is initiated by leaving basic information. User is redirected to AV'40 page, where they will actually
    sign up. Board can see who has signed up this way. There might not be full correspondence between exact signup and
    what is provided to AV'40. So there is a manual check."""
    dsrc: Source = request.app.state.dsrc

    u_ex = await data.user.user_exists(dsrc, signup.email)
    su_ex = await data.signedup.signedup_exists(dsrc, signup.email)

    do_send_email = not u_ex and not su_ex
    logger.debug(f"{signup.email} /onboard/signup - do_send_email {do_send_email}")

    confirm_id = util.random_time_hash_hex()

    await data.kv.store_email_confirmation(dsrc, confirm_id, signup)
    config: Config = request.app.state.config

    params = {
        "confirm_id": confirm_id
    }
    confirmation_url = f"{credentials_url}email/?{urlencode(params)}"

    if do_send_email:
        send_signup_email(background_tasks, signup.email, config.MAIL_PASS, confirmation_url, signup_url)
    else:
        # Prevent client enumeration
        await sleep(0.00002)

    return None


@router.post("/onboard/email/")
async def email_confirm(confirm_req: EmailConfirm, request: Request):
    dsrc: Source = request.app.state.dsrc

    try:
        signup = await data.kv.get_email_confirmation(dsrc, confirm_req.confirm_id)
    except NoDataError as e:
        logger.debug(e.message)
        reason = "Incorrect confirm ID or expired."
        raise ErrorResponse(400, err_type="invalid_signup", err_desc=reason, debug_key="bad_confirm_id")

    signed_up = SignedUp(firstname=signup.firstname, lastname=signup.lastname, email=signup.email, phone=signup.phone)

    try:
        async with data.get_conn(dsrc) as conn:
            await data.signedup.insert_su_row(dsrc, conn, signed_up.dict())
    except DataError as e:
        logger.debug(e.message)
        if e.key == "unique_violation":
            raise ErrorResponse(400, err_type="invalid_signup", err_desc="Email already exists!",
                                debug_key="user_exists")
        else:
            raise e

    return None


@router.get("/onboard/get/", response_model=list[SignedUp])
async def get_signedup(request: Request, authorization: str = Security(auth_header)):
    dsrc: Source = request.app.state.dsrc
    await require_admin(authorization, dsrc)
    async with data.get_conn(dsrc) as conn:
        signed_up = await data.signedup.get_all_signedup(dsrc, conn)
    return signed_up


@router.post("/onboard/confirm/")
async def confirm_join(signup: SignupConfirm, request: Request, background_tasks: BackgroundTasks,
                       authorization: str = Security(auth_header)):
    """ Board confirms data from AV`40 signup through admin tool. """
    dsrc: Source = request.app.state.dsrc
    await require_admin(authorization, dsrc)

    try:
        async with data.get_conn(dsrc) as conn:
            signed_up = await data.signedup.get_signedup_by_email(dsrc, conn, signup.email)
    except DataError as e:
        logger.debug(e.message)
        if e.key == "signedup_empty":
            raise ErrorResponse(400, err_type="invalid_onboard", err_desc="No user under this e-mail in signup!",
                                debug_key="no_user_signup")
        else:
            raise e

    # Success here means removing any existing records in signedup and also the KV relating to that email

    register_id = util.random_time_hash_hex(short=True)
    async with data.get_conn(dsrc) as conn:
        await data.user.new_user(dsrc, conn, signed_up, register_id, av40id=signup.av40id, joined=signup.joined)
        await data.signedup.confirm_signup(dsrc, conn, signup.email)

    config: Config = request.app.state.config

    info = {
        "register_id": register_id,
        "firstname": signed_up.firstname,
        "lastname": signed_up.lastname,
        "email": signed_up.email,
        "phone": signed_up.phone
    }
    info_str = util.enc_b64url(json.dumps(info).encode('utf-8'))
    params = {
        "info": info_str
    }
    registration_url = f"{credentials_url}register/?{urlencode(params)}"

    send_register_email(background_tasks, signup.email, config.MAIL_PASS, registration_url)


@router.post("/onboard/register/", response_model=PasswordResponse)
async def start_register(register_start: RegisterRequest, request: Request):
    """ First step of OPAQUE registration, requires username and client message generated in first client registration
    step."""
    dsrc: Source = request.app.state.dsrc
    try:
        async with data.get_conn(dsrc) as conn:
            ud = await data.user.get_userdata_by_register_id(dsrc, conn, register_start.register_id)
    except NoDataError as e:
        logger.debug(e)
        reason = "No registration for that register_id"
        raise ErrorResponse(400, err_type="invalid_register", err_desc=reason, debug_key="no_register_for_id")

    try:
        async with data.get_conn(dsrc) as conn:
            u = await data.user.get_user_by_id(dsrc, conn, ud.user_id)
    except DataError as e:
        logger.debug(e)
        reason = "No registration for that user"
        raise ErrorResponse(400, err_type="invalid_register", err_desc=reason, debug_key="no_register_for_user")

    if ud.registered or len(u.password_file) > 0:
        logger.debug("Already registered.")
        reason = "Bad registration."
        raise ErrorResponse(400, err_type="invalid_register", err_desc=reason, debug_key="bad_registration_start")

    if u.email != register_start.email:
        logger.debug("Registration start does not match e-mail")
        reason = "Bad registration."
        raise ErrorResponse(400, err_type="invalid_register", err_desc=reason, debug_key="bad_registration_start")

    return await send_register_start(dsrc, ud.user_id, register_start.client_request)


@router.post("/onboard/finish/")
async def finish_register(register_finish: FinishRequest, request: Request):
    """ At this point, we have info saved under 'userdata', 'users' and short-term storage as SavedRegisterState. All
    this data must match up for there to be a succesful registration. """
    dsrc: Source = request.app.state.dsrc
    try:
        saved_state = await data.kv.get_register_state(dsrc, register_finish.auth_id)
    except NoDataError as e:
        logger.debug(e.message)
        reason = "Registration not initialized or expired."
        raise ErrorResponse(400, err_type="invalid_registration", err_desc=reason, debug_key="no_register_start")

    # Generate password file
    # Note that this is equal to the client request
    password_file = opq.register_finish(register_finish.client_request)

    try:
        async with data.get_conn(dsrc) as conn:
            ud = await data.user.get_userdata_by_register_id(dsrc, conn, register_finish.register_id)
    except NoDataError as e:
        logger.debug(e)
        reason = "No registration for that register_id."
        raise ErrorResponse(400, err_type="invalid_register", err_desc=reason, debug_key="no_register_for_id")

    if ud.registered:
        logger.debug("Already registered.")
        reason = "Bad registration."
        raise ErrorResponse(400, err_type="invalid_register", err_desc=reason, debug_key="bad_registration")

    if ud.email != register_finish.email:
        logger.debug("Registration does not match e-mail.")
        reason = "Bad registration."
        raise ErrorResponse(400, err_type="invalid_register", err_desc=reason, debug_key="bad_registration")

    new_userdata = UserData(user_id=ud.user_id, firstname=ud.firstname, lastname=ud.lastname,
                            callname=register_finish.callname, email=ud.email, phone=ud.phone, av40id=ud.av40id,
                            joined=ud.joined, eduinstitution=register_finish.eduinstitution,
                            birthdate=register_finish.birthdate, registerid=ud.registerid, active=True, registered=True)

    async with data.get_conn(dsrc) as conn:
        await data.user.update_password_file(dsrc, conn, saved_state.user_id, password_file)
        await data.user.upsert_userdata(dsrc, conn, new_userdata)

    # send welcome email
