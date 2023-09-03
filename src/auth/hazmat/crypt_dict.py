import secrets
from typing import Any

from cryptography.exceptions import InvalidTag, InvalidSignature, InvalidKey
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from auth.core.util import enc_dict, enc_b64url, dec_b64url, dec_dict


def encrypt_dict(aesgcm: AESGCM, dct: dict[str, Any]) -> str:
    # 12 byte / 96 bit IV/nonce used as recommended for AESGCM
    # Regenerated every time
    dict_data = enc_dict(dct)
    dict_nonce = secrets.token_bytes(12)
    # Cryptography ensures a 16 byte / 128 bit authentication tag is appended
    encrypted = aesgcm.encrypt(dict_nonce, dict_data, None)
    refresh_bytes = dict_nonce + encrypted
    return enc_b64url(refresh_bytes)


class DecryptError(Exception):
    pass


def decrypt_dict(aesgcm: AESGCM, b64url_crypt_dict: str) -> dict[str, Any]:
    crypt_dict_bytes = dec_b64url(b64url_crypt_dict)
    crypt_dict_nonce = crypt_dict_bytes[:12]
    crypt_dict_data = crypt_dict_bytes[12:]
    # The 16 byte / 128 bit authentication tag is automatically checked by cryptography
    try:
        decrypted = aesgcm.decrypt(crypt_dict_nonce, crypt_dict_data, None)
    except (InvalidTag, InvalidSignature, InvalidKey):
        raise DecryptError
    return dec_dict(decrypted)
