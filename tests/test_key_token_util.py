from typing import Optional
from apiserver.define import DEFINE, refresh_exp, access_exp, id_exp
from apiserver.lib.hazmat.keys import (
    ed448_private_to_pem,
    new_ed448_keypair,
    new_symmetric_key,
)
from auth.core.model import AuthKeys
from auth.core.util import dec_b64url, utc_timestamp
from auth.data.relational.user import EmptyIdUserData
from auth.hazmat.key_decode import aes_from_symmetric
from auth.token.build import create_tokens, finish_tokens


def gen_auth_keys(kid_sig: str, kid_enc: str, kid_enc_old: str):
    sig_jwk = new_ed448_keypair(kid_sig)
    sig_private_bytes = dec_b64url(sig_jwk.d)
    _, signing_key = ed448_private_to_pem(sig_private_bytes, kid_sig)
    symm_jwk = new_symmetric_key(kid_enc)
    symmetric_key = aes_from_symmetric(symm_jwk.k)
    symm_jwk_old = new_symmetric_key(kid_enc_old)
    symmetric_key_old = aes_from_symmetric(symm_jwk_old.k)

    return AuthKeys(
        symmetric=symmetric_key, old_symmetric=symmetric_key_old, signing=signing_key
    )


def generate_tokens(
    user_id: str,
    scope: str,
    refresh_id: int,
    keys: AuthKeys,
    utc_now: Optional[int] = None,
):
    utc_now = utc_timestamp() if utc_now is None else utc_now
    id_userdata = EmptyIdUserData()
    access_token_data, id_token_data, access_scope, refresh_save = create_tokens(
        user_id,
        scope,
        utc_now - 1,
        "test_nonce",
        utc_now,
        id_userdata,
        DEFINE.issuer,
        DEFINE.frontend_client_id,
        DEFINE.backend_client_id,
        refresh_exp,
    )

    refresh_token, access_token, id_token = finish_tokens(
        refresh_id,
        refresh_save,
        keys.symmetric,
        access_token_data,
        id_token_data,
        id_userdata,
        utc_now,
        keys.signing,
        access_exp,
        id_exp,
        nonce="",
    )

    return refresh_token, access_token, id_token
