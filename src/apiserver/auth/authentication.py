import opaquepy as opq

from apiserver.define import SavedRegisterState


def opaque_register(client_request, public_key, user_usph, user_id):
    response, state = opq.register(client_request, public_key)
    return response, SavedRegisterState(user_usph=user_usph, id=user_id, state=state)
