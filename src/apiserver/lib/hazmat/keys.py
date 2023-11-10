import opaquepy as opq
from cryptography.hazmat.primitives.asymmetric.ed448 import Ed448PrivateKey
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.serialization import (
    PrivateFormat,
    PublicFormat,
    Encoding,
    NoEncryption,
)

from apiserver.lib.model.entities import JWKPairEdDSA, JWKSymmetricA256GCM, PEMKey
from auth.core.util import enc_b64url
from auth.data.relational.entities import OpaqueSetup
from auth.hazmat.structs import PEMPrivateKey


def new_ed448_keypair(kid: str) -> JWKPairEdDSA:
    private_key = Ed448PrivateKey.generate()
    d_bytes = private_key.private_bytes(Encoding.Raw, PrivateFormat.Raw, NoEncryption())
    x_bytes = private_key.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)

    return JWKPairEdDSA(
        kty="OKP",
        use="sig",
        alg="EdDSA",
        crv="Ed448",
        x=enc_b64url(x_bytes),
        d=enc_b64url(d_bytes),
        kid=kid,
    )


def ed448_private_to_pem(
    private_bytes: bytes, kid: str
) -> tuple[PEMKey, PEMPrivateKey]:
    private_key = Ed448PrivateKey.from_private_bytes(private_bytes)

    private = private_key.private_bytes(
        Encoding.PEM, PrivateFormat.PKCS8, NoEncryption()
    ).decode(encoding="utf-8")
    public = (
        private_key.public_key()
        .public_bytes(Encoding.PEM, PublicFormat.SubjectPublicKeyInfo)
        .decode(encoding="utf-8")
    )

    return PEMKey(kid=kid, public=public), PEMPrivateKey(
        kid=kid, public=public, private=private
    )


def gen_pw_file(setup: str, password: str, client_cred: str) -> str:
    cl_req, cl_state = opq.register_client(password)
    serv_resp = opq.register(setup, cl_req, client_cred)
    cl_fin = opq.register_client_finish(cl_state, password, serv_resp)
    return opq.register_finish(cl_fin)


def new_opaque_setup(id_int: int) -> OpaqueSetup:
    value = opq.create_setup()

    new_setup = OpaqueSetup(value=value, id=id_int)

    return new_setup


def new_symmetric_key(kid: str) -> JWKSymmetricA256GCM:
    symmetric_bytes = AESGCM.generate_key(256)
    symmetric = enc_b64url(symmetric_bytes)

    return JWKSymmetricA256GCM(
        kty="oct", use="enc", alg="A256GCM", k=symmetric, kid=kid
    )
