from auth.core.error import RefreshOperationError
from auth.core.model import IdInfo
from auth.data.schemad.entities import SavedRefreshToken
from auth.data.schemad.ops import SchemaOps
from store import Store
from store.conn import get_conn
from store.error import NoDataError


async def get_id_info(store: Store, ops: SchemaOps, user_id: str) -> IdInfo:
    async with get_conn(store) as conn:
        ud = await ops.userdata.get_userdata_by_id(conn, user_id)

    return ops.userdata.id_info_from_ud(ud)


async def add_refresh_token(
    store: Store, ops: SchemaOps, refresh_save: SavedRefreshToken
):
    async with get_conn(store) as conn:
        refresh_id = await ops.refresh.insert_refresh_row(conn, refresh_save)

    return refresh_id


async def delete_refresh_token(store: Store, ops: SchemaOps, family_id: str):
    async with get_conn(store) as conn:
        await ops.refresh.delete_family(conn, family_id)


async def get_saved_refresh(
    store: Store, ops: SchemaOps, old_refresh
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


async def replace_refresh(
    store: Store,
    ops: SchemaOps,
    old_refresh_id: int,
    new_refresh_save: SavedRefreshToken,
):
    async with get_conn(store) as conn:
        await ops.refresh.delete_refresh_by_id(conn, old_refresh_id)
        new_refresh_id = await ops.refresh.insert_refresh_row(conn, new_refresh_save)

    return new_refresh_id
