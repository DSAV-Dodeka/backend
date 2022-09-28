from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.asymmetric.ed448 import Ed448PrivateKey
from cryptography.hazmat.primitives.serialization import PrivateFormat, PublicFormat, Encoding, NoEncryption
from opaquepy import create_setup as opaque_create_setup
from pydantic import BaseModel

from apiserver.utilities import enc_b64url
from apiserver.define.entities import OpaqueSetup, TokenKey, SymmetricKey, PEMKey


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


def ed448_private_to_pem(private_bytes: bytes, kid: str) -> PEMKey:
    private_key = Ed448PrivateKey.from_private_bytes(private_bytes)

    private = private_key.private_bytes(Encoding.PEM, PrivateFormat.PKCS8, NoEncryption()).decode(
        encoding='utf-8')
    public = private_key.public_key().public_bytes(Encoding.PEM, PublicFormat.SubjectPublicKeyInfo).decode(
        encoding="utf-8")

    return PEMKey(kid=kid, public=public, private=private)


def new_opaque_setup(id_int: int) -> OpaqueSetup:
    value = opaque_create_setup()

    new_setup = OpaqueSetup(value=value, id=id_int)

    return new_setup


def new_symmetric_key() -> str:
    symmetric_bytes = AESGCM.generate_key(256)
    symmetric = enc_b64url(symmetric_bytes)

    return symmetric
