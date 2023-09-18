from auth.data.schemad.ops import SchemaOps
from store import Store
from store.conn import get_conn


async def update_password(store: Store, ops: SchemaOps, user_id: str, new_pw_file: str):
    async with get_conn(store) as conn:
        await ops.user.update_password_file(conn, user_id, new_pw_file)