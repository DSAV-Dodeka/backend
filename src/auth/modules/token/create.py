from auth.core.error import InvalidRefresh
from auth.data.context import TokenContext
from auth.data.keys import get_keys
from auth.data.token import (
    get_id_userdata,
    get_saved_refresh,
    add_refresh_token,
    replace_refresh,
    delete_refresh_token,
)
from auth.token.build import build_refresh_save, create_tokens, finish_tokens
from auth.token.crypt_token import decrypt_old_refresh
from auth.hazmat.verify_token import verify_refresh
from auth.core.model import Tokens, KeyState
from auth.core.util import utc_timestamp
from auth.data.relational.ops import RelationOps
from auth.define import grace_period, access_exp, id_exp, refresh_exp, Define
from store import Store
from store.conn import store_session


async def do_refresh(
    store: Store,
    ops: RelationOps,
    context: TokenContext,
    key_state: KeyState,
    old_refresh_token: str,
) -> Tokens:
    keys = await get_keys(context, store, key_state)
    old_refresh = decrypt_old_refresh(
        keys.symmetric, keys.old_symmetric, old_refresh_token
    )

    utc_now = utc_timestamp()

    saved_refresh = await get_saved_refresh(context, store, ops, old_refresh)

    verify_refresh(saved_refresh, old_refresh, utc_now, grace_period)

    (
        access_token_data,
        id_token_data,
        id_userdata,
        user_id,
        access_scope,
        new_nonce,
        new_refresh_save,
    ) = build_refresh_save(saved_refresh, utc_now, ops.id_userdata.get_type())

    # Deletes previous token, saves new one, only succeeds if all components of the
    # transaction succeed
    new_refresh_id = await replace_refresh(
        context, store, ops, old_refresh.id, new_refresh_save
    )

    refresh_token, access_token, id_token = finish_tokens(
        new_refresh_id,
        new_refresh_save,
        keys.symmetric,
        access_token_data,
        id_token_data,
        id_userdata,
        utc_now,
        keys.signing,
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
    ops: RelationOps,
    context: TokenContext,
    key_state: KeyState,
    user_id: str,
    scope: str,
    auth_time: int,
    id_nonce: str,
) -> Tokens:
    # THROWS UnexpectedError if keys are not present
    keys = await get_keys(context, store, key_state)

    utc_now = utc_timestamp()

    async with store_session(store) as session:
        # THROWS AuthError if user does not exist
        id_userdata = await get_id_userdata(context, session, ops, user_id)

        access_token_data, id_token_data, access_scope, refresh_save = create_tokens(
            user_id,
            scope,
            auth_time,
            id_nonce,
            utc_now,
            id_userdata,
            define.issuer,
            define.frontend_client_id,
            define.backend_client_id,
            refresh_exp,
        )

        # Stores the refresh token in the database
        refresh_id = await add_refresh_token(context, store, ops, refresh_save)

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

    return Tokens(
        id=id_token,
        acc=access_token,
        refr=refresh_token,
        exp=id_exp,
        scope=access_scope,
        user_id=user_id,
    )


async def delete_refresh(
    store: Store,
    ops: RelationOps,
    context: TokenContext,
    key_state: KeyState,
    refresh_token: str,
) -> None:
    keys = await get_keys(context, store, key_state)
    try:
        refresh = decrypt_old_refresh(keys.symmetric, keys.old_symmetric, refresh_token)
    except InvalidRefresh:
        return

    # Do not check rowcount, which would be zero if no token is deleted
    await delete_refresh_token(context, store, ops, refresh.family_id)
