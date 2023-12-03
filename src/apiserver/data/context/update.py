from typing import Optional

from loguru import logger

from apiserver import data
from apiserver.data import Source
from apiserver.data.context import UpdateContext
from auth.core.util import random_time_hash_hex
from datacontext.context import ContextRegistry
from store.error import NoDataError

ctx_reg = ContextRegistry()


@ctx_reg.register(UpdateContext)
async def store_email_flow_password_change(dsrc: Source, email: str) -> Optional[str]:
    """If registered user exists for email, then store email with random flow ID and return it. Else, return None."""
    try:
        async with data.get_conn(dsrc) as conn:
            ud = await data.ud.get_userdata_by_email(conn, email)
    except NoDataError:
        logger.debug(f"No user with email {email}")
        return None

    if not ud.registered:
        logger.debug(f"User {ud.user_id} with email {email} is not registered.")
        return None

    flow_id = random_time_hash_hex()

    await data.trs.store_string(dsrc, flow_id, email, 1000)
    logger.debug(f"Stored flow_id {flow_id} for email: {email}")

    return flow_id
