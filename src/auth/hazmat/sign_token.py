import jwt

from auth.token.build_util import finish_payload
from auth.hazmat.structs import PEMPrivateKey


def finish_encode_token(token_val: dict, utc_now: int, exp: int, key: PEMPrivateKey):
    finished_payload = finish_payload(token_val, utc_now, exp)
    return jwt.encode(
        finished_payload, key.private, algorithm="EdDSA", headers={"kid": key.kid}
    )
