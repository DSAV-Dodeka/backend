from loguru import logger
import opaquepy as opq

from auth.core.model import SavedRegisterState
from auth.core.response import PasswordResponse
from auth.data.authentication import get_apake_setup
from auth.data.context import RegisterContext
from auth.data.register import store_auth_register_state
from store import Store


async def send_register_start(
    store: Store, context: RegisterContext, user_id: str, client_request: str
) -> PasswordResponse:
    """Generates auth_id"""
    apake_setup = await get_apake_setup(context, store)

    response = opq.register(apake_setup, client_request, user_id)
    saved_state = SavedRegisterState(user_id=user_id)

    auth_id = await store_auth_register_state(context, store, user_id, saved_state)

    logger.debug(f"Stored register start for user_id {user_id} with auth_id {auth_id}.")
    return PasswordResponse(server_message=response, auth_id=auth_id)
