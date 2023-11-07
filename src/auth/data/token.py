from auth.core.error import RefreshOperationError, AuthError
from auth.core.model import RefreshToken
from auth.data.context import TokenContext
from auth.data.relational.entities import SavedRefreshToken
from auth.data.relational.ops import RelationOps
from auth.data.relational.user import IdUserData
from datacontext.context import ContextRegistry
from store import Store
from store.conn import get_conn
from store.error import NoDataError

ctx_reg = ContextRegistry()


@ctx_reg.register(TokenContext)
async def get_id_userdata(store: Store, ops: RelationOps, user_id: str) -> IdUserData:
    async with get_conn(store) as conn:
        try:
            return await ops.id_userdata.get_id_userdata_by_id(conn, user_id)
        except NoDataError:
            raise AuthError("invalid_grant", "User for grant no longer exists.")


@ctx_reg.register(TokenContext)
async def add_refresh_token(
    store: Store, ops: RelationOps, refresh_save: SavedRefreshToken
) -> int:
    async with get_conn(store) as conn:
        refresh_id = await ops.refresh.insert_refresh_row(conn, refresh_save)

    return refresh_id


@ctx_reg.register(TokenContext)
async def delete_refresh_token(store: Store, ops: RelationOps, family_id: str) -> int:
    async with get_conn(store) as conn:
        return await ops.refresh.delete_family(conn, family_id)


async def delete_refresh_token_by_user(
    store: Store, ops: RelationOps, user_id: str
) -> None:
    async with get_conn(store) as conn:
        await ops.refresh.delete_by_user_id(conn, user_id)


@ctx_reg.register(TokenContext)
async def get_saved_refresh(
    store: Store, ops: RelationOps, old_refresh: RefreshToken
) -> SavedRefreshToken:
    async with get_conn(store) as conn:
        try:
            # See if previous refresh exists
            saved_refresh = await ops.refresh.get_refresh_by_id(conn, old_refresh.id)
        except NoDataError as e:
            if e.key != "refresh_empty":
                # If not refresh_empty, it was some other internal error
                raise e
            # Only the most recent token should be valid and is always returned
            # So if someone possesses some deleted token family member, it is most
            # likely an attacker. For this reason, all tokens in the family are
            # invalidated to prevent further compromise
            await ops.refresh.delete_family(conn, old_refresh.family_id)
            raise RefreshOperationError("Not recent")

    return saved_refresh


@ctx_reg.register(TokenContext)
async def replace_refresh(
    store: Store,
    ops: RelationOps,
    old_refresh_id: int,
    new_refresh_save: SavedRefreshToken,
) -> int:
    async with get_conn(store) as conn:
        await ops.refresh.delete_refresh_by_id(conn, old_refresh_id)
        new_refresh_id = await ops.refresh.insert_refresh_row(conn, new_refresh_save)

    return new_refresh_id
