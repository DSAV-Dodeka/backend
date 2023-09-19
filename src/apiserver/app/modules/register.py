from datetime import date

from pydantic import BaseModel
import opaquepy as opq

from apiserver.app.error import AppError, ErrorKeys
from apiserver.data.frame import RegisterFrame
from apiserver.data import Source
from apiserver.data.api.ud.userdata import finished_userdata


class RegisterRequest(BaseModel):
    email: str
    client_request: str
    register_id: str


async def check_register(
    dsrc: Source, frame: RegisterFrame, register_start: RegisterRequest
) -> str:
    ud, u = await frame.get_registration(dsrc, register_start.register_id)

    if ud.registered or len(u.password_file) > 0:
        # logger.debug("Already registered.")
        reason = "Bad registration."
        raise AppError(
            err_type=ErrorKeys.REGISTER,
            err_desc=reason,
            debug_key="bad_registration_start",
        )

    if u.email != register_start.email.lower():
        # logger.debug("Registration start does not match e-mail")
        reason = "Bad registration."
        raise AppError(
            err_type=ErrorKeys.REGISTER,
            err_desc=reason,
            debug_key="bad_registration_start",
        )

    return ud.user_id


class FinishRequest(BaseModel):
    auth_id: str
    email: str
    client_request: str
    register_id: str
    callname: str
    eduinstitution: str
    birthdate: date
    age_privacy: bool


async def finalize_save_register(
    dsrc: Source, frame: RegisterFrame, register_finish: FinishRequest
):
    saved_state = await frame.get_register_state(dsrc, register_finish.auth_id)

    # Generate password file
    # Note that this is equal to the client request, it simply is a check for correct format
    try:
        password_file = opq.register_finish(register_finish.client_request)
    except ValueError as e:
        # logger.debug(f"OPAQUE failure from client OPAQUE message: {e!s}")
        raise AppError(
            err_type=ErrorKeys.REGISTER,
            err_desc="Invalid OPAQUE registration.",
            debug_key="bad_opaque_registration",
        )

    ud = await frame.check_userdata_register(
        dsrc, register_finish.register_id, register_finish.email, saved_state.user_id
    )

    new_userdata = finished_userdata(
        ud,
        register_finish.callname,
        register_finish.eduinstitution,
        register_finish.birthdate,
        register_finish.age_privacy,
    )

    await frame.save_registration(dsrc, password_file, new_userdata)
