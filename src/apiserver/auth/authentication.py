import opaquepy as opq

from apiserver.define import SavedRegisterState, PasswordResponse
import apiserver.utilities as util
import apiserver.data as data
from apiserver.data import Source


async def send_register_start(dsrc: Source, user_usph: str, client_request: str, user_id: int):
    """ Generates auth_id """
    auth_id = util.random_time_hash_hex(user_usph)

    async with data.get_conn(dsrc) as conn:
        opaque_setup = await data.opaquesetup.get_setup(dsrc, conn)

    response = opq.register(opaque_setup, client_request, user_usph)
    saved_state = SavedRegisterState(user_usph=user_usph, id=user_id)
    await data.kv.store_auth_register_state(dsrc, auth_id, saved_state)

    return PasswordResponse(server_message=response, auth_id=auth_id)
