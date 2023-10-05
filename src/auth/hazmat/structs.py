from dataclasses import dataclass

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from pydantic import BaseModel


class PEMPrivateKey(BaseModel):
    kid: str  # Same as the public-only key, stored with '_private' appended.
    public: str  # PEM encoded X509PKCS#1 (decoded as utf-8)
    private: str  # PEM encoded PKCS#8 (decoded as utf-8)


class A256GCMKey(BaseModel):
    kid: str
    symmetric: str  # base64url encoded symmetric 256-bit key


@dataclass
class SymmetricKey:
    private: AESGCM
