from apiserver.data import Source, get_kv, NoDataError
from apiserver.data.kv import store_json, get_json, pop_json
from apiserver.lib.model.entities import SavedRegisterState, UpdateEmailState, Signup


async def store_auth_register_state(
    dsrc: Source, auth_id: str, state: SavedRegisterState
):
    await store_json(get_kv(dsrc), auth_id, state.dict(), expire=1000)


async def get_register_state(dsrc: Source, auth_id: str) -> SavedRegisterState:
    state_dict: dict = await get_json(get_kv(dsrc), auth_id)
    if state_dict is None:
        raise NoDataError("State does not exist or expired.", "saved_state_empty")
    return SavedRegisterState.parse_obj(state_dict)


async def store_email_confirmation(
    dsrc: Source, confirm_id: str, signup: Signup, email_expiration
):
    await store_json(get_kv(dsrc), confirm_id, signup.dict(), expire=email_expiration)


async def get_email_confirmation(dsrc: Source, confirm_id: str) -> Signup:
    signup_dict: dict = await get_json(get_kv(dsrc), confirm_id)
    if signup_dict is None:
        raise NoDataError(
            "Confirmation ID does not exist or expired.", "saved_confirm_empty"
        )
    return Signup.parse_obj(signup_dict)


async def store_update_email(
    dsrc: Source, flow_id: str, update_email: UpdateEmailState
):
    await store_json(get_kv(dsrc), flow_id, update_email.dict(), expire=1000)


async def get_update_email(dsrc: Source, flow_id: str) -> UpdateEmailState:
    email_dict: dict = await pop_json(get_kv(dsrc), flow_id)
    if email_dict is None:
        raise NoDataError(
            "Flow ID does not exist or expired.", "saved_email_update_empty"
        )
    return UpdateEmailState.parse_obj(email_dict)
