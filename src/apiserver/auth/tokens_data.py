from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from apiserver.define import id_exp
from apiserver.utilities import utc_timestamp
from apiserver.auth.tokens import aes_from_symmetric, decrypt_old_refresh, InvalidRefresh, verify_refresh, \
    build_refresh_save, finish_tokens, create_tokens
import apiserver.data as data
from apiserver.data import Source, DataError


async def get_keys(dsrc: Source) -> tuple[AESGCM, str]:
    # Symmetric key used to verify and encrypt/decrypt refresh tokens
    symmetric_key = await data.key.get_refresh_symmetric(dsrc)
    aesgcm = aes_from_symmetric(symmetric_key)
    # Asymmetric private key used for signing access and ID tokens
    # A public key is then used to verify them
    signing_key = await data.key.get_token_private(dsrc)

    return aesgcm, signing_key


async def do_refresh(dsrc: Source, old_refresh_token: str):
    aesgcm, signing_key = await get_keys(dsrc)
    utc_now = utc_timestamp()

    old_refresh = decrypt_old_refresh(aesgcm, old_refresh_token)

    try:
        # See if previous refresh exists
        saved_refresh = await data.refreshtoken.get_refresh_by_id(dsrc, old_refresh.id)
    except DataError as e:
        if e.key != "refresh_empty":
            # If not refresh_empty, it was some other internal error
            raise e
        # Only the most recent token should be valid and is always returned
        # So if someone possesses some deleted token family member, it is most likely an attacker
        # For this reason, all tokens in the family are invalidated to prevent further compromise
        await data.refreshtoken.delete_family(dsrc, old_refresh.family_id)
        raise InvalidRefresh("Not recent")

    verify_refresh(saved_refresh, old_refresh, utc_now)

    access_token_data, id_token_data, user_usph, access_scope, \
        new_nonce, new_refresh_save = build_refresh_save(saved_refresh, utc_now)

    # Deletes previous token, saves new one, only succeeds if all components of the transaction succeed
    new_refresh_id = await data.refreshtoken.refresh_transaction(dsrc, saved_refresh.id, new_refresh_save)

    refresh_token, access_token, id_token = finish_tokens(new_refresh_id, new_refresh_save, aesgcm, access_token_data,
                                                          id_token_data, utc_now, signing_key, nonce=new_nonce)

    return id_token, access_token, refresh_token, id_exp, access_scope, user_usph


async def new_token(dsrc: Source, user_usph: str, scope: str, auth_time: int, id_nonce: str):
    aesgcm, signing_key = await get_keys(dsrc)
    utc_now = utc_timestamp()

    access_token_data, id_token_data, access_scope, refresh_save = create_tokens(user_usph, scope, auth_time, id_nonce,
                                                                                 utc_now)

    refresh_id = await data.refreshtoken.refresh_save(dsrc, refresh_save)

    refresh_token, access_token, id_token = finish_tokens(refresh_id, refresh_save, aesgcm, access_token_data,
                                                          id_token_data, utc_now, signing_key, nonce="")

    return id_token, access_token, refresh_token, id_exp, access_scope
