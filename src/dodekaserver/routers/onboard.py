import logging

from fastapi import APIRouter, Security, status, HTTPException

from dodekaserver.env import LOGGER_NAME
from dodekaserver.define import ErrorResponse
from dodekaserver.define.entities import AccessToken, SignedUp, UserData
from dodekaserver.define.request import SignupRequest, SignupConfirm, Register, UserDataRegisterResponse
import dodekaserver.utilities as util
from dodekaserver.auth.header import auth_header
import dodekaserver.data as data
from dodekaserver.data import DataError
from dodekaserver.routers.helper import require_admin


dsrc = data.dsrc

router = APIRouter()

logger = logging.getLogger(LOGGER_NAME)


@router.post("/onboard/signup")
async def init_signup(signup: SignupRequest):
    """ Signup is initiated by leaving basic information. User is redirected to AV'40 page, where they will actually
    sign up. Board can see who has signed up this way. There might not be full correspondence between exact signup and
    what is provided to AV'40. So there is a manual check."""
    print(signup.dict())
    signed_up = SignedUp(firstname=signup.firstname, lastname=signup.lastname, email=signup.email, phone=signup.phone)
    await data.signedup.insert_su_row(dsrc, signed_up.dict())
    # send info email

    return {
        "ok": "ok"
    }


@router.post("/onboard/confirm")
async def confirm_join(signup: SignupConfirm, authorization: str = Security(auth_header)):
    """ Board confirms data from AV`40 signup through admin tool. """
    await require_admin(authorization)

    signed_up = await data.signedup.get_signedup_by_email(dsrc, signup.email)
    email_usph = util.usp_hex(signup.email)
    register_id = util.random_time_hash_hex(email_usph)
    await data.user.new_user(dsrc, signed_up, register_id, av40id=signup.av40id, joined=signup.joined)

    # send register email

    return {
        "ok": "ok"
    }


@router.get("/onboard/userdata/{register_id}")
async def register_id_userdata(register_id: str):

    try:
        ud = await data.user.get_userdata_by_register_id(dsrc, register_id)
    except DataError as e:
        logger.debug(e)
        reason = "No registration for that register_id"
        raise ErrorResponse(400, err_type="invalid_register", err_desc=reason, debug_key="no_register_for_id")

    return UserDataRegisterResponse(email=ud.email, firstname=ud.firstname, lastname=ud.lastname, phone=ud.phone)


@router.post("/onboard/register")
async def register_user(register: Register):
    """ Board confirms data from AV`40 signup through admin tool. """
    email_usph = util.usp_hex(register.email)
    try:
        ud = await data.user.get_userdata_by_register_id(dsrc, register.registerid)
    except DataError as e:
        logger.debug(e)
        reason = "No registration for that register_id"
        raise ErrorResponse(400, err_type="invalid_register", err_desc=reason, debug_key="no_register_for_id")

    if ud.registered:
        logger.debug("Already registered.")
        reason = "Bad registration."
        raise ErrorResponse(400, err_type="invalid_register", err_desc=reason, debug_key="bad_registration")

    if ud.email != email_usph:
        logger.debug("Registration does not match e-mail")
        reason = "Bad registration."
        raise ErrorResponse(400, err_type="invalid_register", err_desc=reason, debug_key="bad_registration")

    new_userdata = UserData(id=ud.id, firstname=ud.firstname, lastname=ud.lastname,  callname=register.callname,
                            email=ud.email, phone=ud.phone, av40id=ud.av40id, joined=ud.joined,
                            eduinstitution=register.eduinstitution, birthdate=register.birthdate, active=True,
                            registered=True)

    await data.user.upsert_userdata(dsrc, new_userdata)

    # send welcome email

    return {
        "ok": "ok"
    }
