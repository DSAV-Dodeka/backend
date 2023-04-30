from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from apiserver.lib.errors import InvalidRefresh
from apiserver.lib.utilities.crypto import aes_from_symmetric
from apiserver.lib.utilities import utc_timestamp
from apiserver.lib.model.entities import PEMKey
from apiserver.lib.model.fn.tokens import (
    decrypt_old_refresh,
    verify_refresh,
    build_refresh_save,
    finish_tokens,
    create_tokens,
    id_info_from_ud,
)
from apiserver import data
from apiserver.data import Source, DataError
from apiserver.app.define import (
    id_exp,
    grace_period,
    issuer,
    backend_client_id,
    refresh_exp,
    frontend_client_id,
    access_exp,
)
from apiserver.app.ops.errors import RefreshOperationError


async def get_keys(dsrc: Source) -> tuple[AESGCM, AESGCM, PEMKey]:
    symmetric_kid = dsrc.state.current_symmetric
    old_symmetric_kid = dsrc.state.current_symmetric
    signing_kid = dsrc.state.current_pem

    # Symmetric key used to verify and encrypt/decrypt refresh tokens
    symmetric_key = await data.trs.key.get_symmetric_key(dsrc, symmetric_kid)
    aesgcm = aes_from_symmetric(symmetric_key.symmetric)
    old_symmetric_key = await data.trs.key.get_symmetric_key(dsrc, old_symmetric_kid)
    old_aesgcm = aes_from_symmetric(old_symmetric_key.symmetric)
    # Asymmetric private key used for signing access and ID tokens
    # A public key is then used to verify them
    signing_key = await data.trs.key.get_pem_key(dsrc, signing_kid)

    return aesgcm, old_aesgcm, signing_key


async def do_refresh(dsrc: Source, old_refresh_token: str):
    aesgcm, old_aesgcm, signing_key = await get_keys(dsrc)
    old_refresh = decrypt_old_refresh(aesgcm, old_aesgcm, old_refresh_token)

    utc_now = utc_timestamp()

    async with data.get_conn(dsrc) as conn:
        try:
            # See if previous refresh exists
            saved_refresh = await data.refreshtoken.get_refresh_by_id(
                conn, old_refresh.id
            )
        except DataError as e:
            if e.key != "refresh_empty":
                # If not refresh_empty, it was some other internal error
                raise e
            # Only the most recent token should be valid and is always returned
            # So if someone possesses some deleted token family member, it is most
            # likely an attacker. For this reason, all tokens in the family are
            # invalidated to prevent further compromise
            await data.refreshtoken.delete_family(conn, old_refresh.family_id)
            raise RefreshOperationError("Not recent")

    verify_refresh(saved_refresh, old_refresh, utc_now, grace_period)

    (
        access_token_data,
        id_token_data,
        user_id,
        access_scope,
        new_nonce,
        new_refresh_save,
    ) = build_refresh_save(saved_refresh, utc_now)

    # Deletes previous token, saves new one, only succeeds if all components of the
    # transaction succeed
    async with data.get_conn(dsrc) as conn:
        await data.refreshtoken.delete_refresh_by_id(conn, saved_refresh.id)
        new_refresh_id = await data.refreshtoken.insert_refresh_row(
            conn, new_refresh_save
        )

    refresh_token, access_token, id_token = finish_tokens(
        new_refresh_id,
        new_refresh_save,
        aesgcm,
        access_token_data,
        id_token_data,
        utc_now,
        signing_key,
        access_exp,
        id_exp,
        nonce=new_nonce,
    )

    return id_token, access_token, refresh_token, id_exp, access_scope, user_id


async def new_token(
    dsrc: Source, user_id: str, scope: str, auth_time: int, id_nonce: str
):
    aesgcm, _, signing_key = await get_keys(dsrc)

    utc_now = utc_timestamp()

    async with data.get_conn(dsrc) as conn:
        ud = await data.user.get_userdata_by_id(conn, user_id)
        id_info = id_info_from_ud(ud)

        access_token_data, id_token_data, access_scope, refresh_save = create_tokens(
            user_id,
            scope,
            auth_time,
            id_nonce,
            utc_now,
            id_info,
            issuer,
            frontend_client_id,
            backend_client_id,
            refresh_exp,
        )

        refresh_id = await data.refreshtoken.insert_refresh_row(conn, refresh_save)

    refresh_token, access_token, id_token = finish_tokens(
        refresh_id,
        refresh_save,
        aesgcm,
        access_token_data,
        id_token_data,
        utc_now,
        signing_key,
        access_exp,
        id_exp,
        nonce="",
    )

    return id_token, access_token, refresh_token, id_exp, access_scope


async def delete_refresh(dsrc: Source, refresh_token: str):
    aesgcm, old_aesgcm, signing_key = await get_keys(dsrc)
    try:
        refresh = decrypt_old_refresh(aesgcm, old_aesgcm, refresh_token)
        print(refresh)
    except InvalidRefresh:
        print("invalid")
        return None

    async with data.get_conn(dsrc) as conn:
        await data.refreshtoken.delete_family(conn, refresh.family_id)
