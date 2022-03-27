from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.asymmetric.ed448 import Ed448PrivateKey
from cryptography.hazmat.primitives.serialization import PrivateFormat, PublicFormat, Encoding, NoEncryption
from opaquepy.lib import generate_keys as opaque_generate_keys

from dodekaserver.utilities import enc_b64url
from dodekaserver.define.entities import OpaqueKey, TokenKey, SymmetricKey


def new_ed448_keypair(id_int: int) -> TokenKey:
    private_key = Ed448PrivateKey.generate()
    # TODO encryption
    private = private_key.private_bytes(Encoding.PEM, PrivateFormat.PKCS8, NoEncryption()).decode(
        encoding='utf-8')
    public = private_key.public_key().public_bytes(Encoding.PEM, PublicFormat.SubjectPublicKeyInfo).decode(
        encoding="utf-8")

    new_key = TokenKey(public=public, private=private, algorithm="ed448", private_format="PKCS#8",
                       public_format="X509PKCS#1", private_encoding="PEM", public_encoding="PEM", id=id_int)

    return new_key


def new_curve25519_keypair(id_int: int) -> OpaqueKey:
    private, public = opaque_generate_keys()

    new_key = OpaqueKey(public=public, private=private, algorithm="curve25519ristretto", private_format="none",
                        public_format="none", private_encoding="base64url", public_encoding="base64url", id=id_int)

    return new_key


def new_symmetric_key(id_int: int) -> SymmetricKey:
    symmetric_bytes = AESGCM.generate_key(256)
    symmetric = enc_b64url(symmetric_bytes)

    new_key = SymmetricKey(private=symmetric, algorithm="symmetric", private_format="none",
                           private_encoding="base64url", id=id_int)

    return new_key
