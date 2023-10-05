from auth import data
from auth.data.schemad.ops import SchemaOps
from store import Store
from store.conn import store_session


async def change_password(store: Store, ops: SchemaOps, new_pw_file: str, user_id: str):
    """Update password file and delete refresh token to force login after access token expires."""
    async with store_session(store) as session:
        await data.update.update_password(session, ops, user_id, new_pw_file)

        await data.token.delete_refresh_token_by_user(session, ops, user_id)
