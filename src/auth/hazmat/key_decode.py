from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from auth.core.util import dec_b64url
from auth.hazmat.structs import SymmetricKey


def aes_from_symmetric(symmetric_key: str) -> SymmetricKey:
    """Symmetric_key is a base64url encoded AES-GCM key."""
    # We store it unpadded (to match convention of not storing padding throughout the DB)
    symmetric_key_bytes = dec_b64url(symmetric_key)
    # We initialize an AES-GCM key class that will be used for encryption/decryption
    # The AESGCm initialization ensures it's always at least 128 bit, but we prefer 256 bit.
    return SymmetricKey(private=AESGCM(symmetric_key_bytes))
