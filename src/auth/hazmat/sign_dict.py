from typing import Any

import jwt

from auth.hazmat.structs import PEMPrivateKey


def sign_dict(key: PEMPrivateKey, dct: dict[str, Any]):
    return jwt.encode(dct, key.private, algorithm="EdDSA", headers={"kid": key.kid})
