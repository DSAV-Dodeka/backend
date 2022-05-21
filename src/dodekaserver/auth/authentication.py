import opaquepy as opq

from dodekaserver.define import SavedState


def opaque_register(client_request, user_usph, public_key):
    response, state = opq.register(client_request, public_key)
    return response, SavedState(user_usph=user_usph, state=state)
