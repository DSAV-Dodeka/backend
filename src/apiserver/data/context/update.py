from typing import Optional

from apiserver import data
from apiserver.data import Source
from apiserver.data.context import UpdateContext
from auth.core.util import random_time_hash_hex
from datacontext.context import ContextRegistry, Context
from store.error import NoDataError

ctx_reg = ContextRegistry()


@ctx_reg.register(UpdateContext)
async def store_email_flow_password_change(
    ctx: Context, dsrc: Source, email: str
) -> Optional[str]:
    """If registered user exists for email, then store email with random flow ID and return it. Else, return None."""
    try:
        async with data.get_conn(dsrc) as conn:
            ud = await data.ud.get_userdata_by_email(conn, email)
    except NoDataError:
        return None

    if not ud.registered:
        return None

    flow_id = random_time_hash_hex()

    await data.trs.store_string(dsrc, flow_id, email, 1000)

    return flow_id
