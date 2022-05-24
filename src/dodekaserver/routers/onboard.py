from fastapi import APIRouter, Security, status, HTTPException

from dodekaserver.define import ErrorResponse
import dodekaserver.data as data
from dodekaserver.auth.header import handle_header, auth_header, BadAuth
from dodekaserver.define.entities import AccessToken, SignedUp
from dodekaserver.define.request import SignupRequest

dsrc = data.dsrc

router = APIRouter()


@router.post("/onboard/signup")
async def init_signup(signup: SignupRequest):

    print(signup.dict())
    signed_up = SignedUp(firstname=signup.firstname, lastname=signup.lastname, email=signup.email, phone=signup.phone)
    await data.signedup.upsert_su_row(dsrc, signed_up.dict())

    return {
        "ok": "ok"
    }
