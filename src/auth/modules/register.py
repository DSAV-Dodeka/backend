import opaquepy as opq

from auth import data
from auth.core.model import SavedRegisterState
from auth.core.response import PasswordResponse
from auth.core.util import random_time_hash_hex
from store import Store


async def send_register_start(store: Store, user_id: str, client_request: str):
    """Generates auth_id"""
    auth_id = random_time_hash_hex(user_id)

    apake_setup = await data.authentication.get_apake_setup(store)

    response = opq.register(apake_setup, client_request, user_id)
    saved_state = SavedRegisterState(user_id=user_id)
    await data.register.store_auth_register_state(store, auth_id, saved_state)

    return PasswordResponse(server_message=response, auth_id=auth_id)
