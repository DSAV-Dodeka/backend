from fastapi import APIRouter, Security, status, HTTPException

from dodekaserver.define import ErrorResponse
import dodekaserver.data as data
from dodekaserver.auth.header import handle_header, auth_header, BadAuth
from dodekaserver.define.entities import AccessToken, SignedUp, UserData
from dodekaserver.define.request import SignupRequest, SignupConfirm
from dodekaserver.utilities import usp_hex

dsrc = data.dsrc

router = APIRouter()


@router.post("/onboard/signup")
async def init_signup(signup: SignupRequest):

    print(signup.dict())
    signed_up = SignedUp(firstname=signup.firstname, lastname=signup.lastname, email=signup.email, phone=signup.phone)
    await data.signedup.insert_su_row(dsrc, signed_up.dict())
    # send info email

    return {
        "ok": "ok"
    }


@router.post("/onboard/confirm")
async def confirm_join(signup: SignupConfirm):
    signed_up = await data.signedup.get_signedup_by_email(dsrc, signup.email)
    await data.user.new_user(dsrc, signed_up, av40id=signup.av40id, joined=signup.joined)

    # send register email

    return {
        "ok": "ok"
    }