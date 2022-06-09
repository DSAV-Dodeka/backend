import opaquepy as opq

from dodekaserver.define import SavedRegisterState


def opaque_register(client_request, user_usph, user_id, public_key):
    response, state = opq.register(client_request, public_key)
    return response, SavedRegisterState(user_usph=user_usph, id=user_id, state=state)
