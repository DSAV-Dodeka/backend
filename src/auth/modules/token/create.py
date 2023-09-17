from auth.core.error import InvalidRefresh
from auth.token.build import build_refresh_save, create_tokens, finish_tokens
from auth.token.crypt_token import decrypt_old_refresh
from auth.hazmat.verify_token import verify_refresh
from auth import data
from auth.core.model import Tokens, KeyState
from auth.core.util import utc_timestamp
from auth.data.keys import get_keys
from auth.data.schemad.ops import SchemaOps
from auth.define import grace_period, access_exp, id_exp, refresh_exp, Define
from store import Store
from store.conn import store_session


async def do_refresh(
    store: Store, ops: SchemaOps, key_state: KeyState, old_refresh_token: str
) -> Tokens:
    symmetric_key, old_symmetric_key, signing_key = await get_keys(store, key_state)
    old_refresh = decrypt_old_refresh(
        symmetric_key, old_symmetric_key, old_refresh_token
    )

    utc_now = utc_timestamp()

    saved_refresh = await data.token.get_saved_refresh(store, ops, old_refresh)

    verify_refresh(saved_refresh, old_refresh, utc_now, grace_period)

    (
        access_token_data,
        id_token_data,
        id_info,
        user_id,
        access_scope,
        new_nonce,
        new_refresh_save,
    ) = build_refresh_save(saved_refresh, ops.userdata.id_info_type(), utc_now)

    # Deletes previous token, saves new one, only succeeds if all components of the
    # transaction succeed
    new_refresh_id = await data.token.replace_refresh(
        store, ops, old_refresh.id, new_refresh_save
    )

    refresh_token, access_token, id_token = finish_tokens(
        new_refresh_id,
        new_refresh_save,
        symmetric_key,
        access_token_data,
        id_token_data,
        id_info,
        utc_now,
        signing_key,
        access_exp,
        id_exp,
        nonce=new_nonce,
    )

    return Tokens(
        id=id_token,
        acc=access_token,
        refr=refresh_token,
        exp=id_exp,
        scope=access_scope,
        user_id=user_id,
    )


async def new_token(
    store: Store,
    define: Define,
    ops: SchemaOps,
    key_state: KeyState,
    user_id: str,
    scope: str,
    auth_time: int,
    id_nonce: str,
):
    # THROWS UnexpectedError if keys are not present
    symmetric_key, _, signing_key = await get_keys(store, key_state)

    utc_now = utc_timestamp()

    async with store_session(store) as session:
        # THROWS AuthError if user does not exist
        id_info = await data.token.get_id_info(session, ops, user_id)

        access_token_data, id_token_data, access_scope, refresh_save = create_tokens(
            user_id,
            scope,
            auth_time,
            id_nonce,
            utc_now,
            id_info,
            define.issuer,
            define.frontend_client_id,
            define.backend_client_id,
            refresh_exp,
        )

        # Stores the refresh token in the database
        refresh_id = await data.token.add_refresh_token(store, ops, refresh_save)

    refresh_token, access_token, id_token = finish_tokens(
        refresh_id,
        refresh_save,
        symmetric_key,
        access_token_data,
        id_token_data,
        id_info,
        utc_now,
        signing_key,
        access_exp,
        id_exp,
        nonce="",
    )

    return Tokens(
        id=id_token,
        acc=access_token,
        refr=refresh_token,
        exp=id_exp,
        scope=access_scope,
        user_id=user_id,
    )


async def delete_refresh(
    store: Store, ops: SchemaOps, key_state: KeyState, refresh_token: str
):
    symmetric_key, old_symmetric_key, signing_key = await get_keys(store, key_state)
    try:
        refresh = decrypt_old_refresh(symmetric_key, old_symmetric_key, refresh_token)
    except InvalidRefresh:
        return None

    # Do not check rowcount, which would be zero if no token is deleted
    await data.token.delete_refresh_token(store, ops, refresh.family_id)
