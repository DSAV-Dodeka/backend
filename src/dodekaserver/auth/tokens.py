from cryptography.hazmat.primitives.asymmetric.ed448 import Ed448PrivateKey
from cryptography.hazmat.primitives.serialization import PrivateFormat, PublicFormat, Encoding, NoEncryption, \
    KeySerializationEncryption, BestAvailableEncryption
import jwt

import dodekaserver.data as data
from dodekaserver.data import Source


__all__ = ['create_access_token']


async def create_access_token(dsrc: Source, user_usph: str):
    private_key = await data.key.get_token_private(dsrc)
    payload = {
        "sub": user_usph,
        "iss": "https://dsavdodeka.nl/auth",
        "aud": ["dodekaweb_client", "dodekabackend_client"]

    }
    return jwt.encode(payload, private_key, algorithm="EdDSA")
