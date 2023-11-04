from typing import Optional

from apiserver import data
from apiserver.app.error import AppError, ErrorKeys
from apiserver.data import Source
from apiserver.data.frame import FrameRegistry
from apiserver.lib.model.entities import UserData
from auth.core.util import random_time_hash_hex
from store.error import NoDataError

frm_upd = FrameRegistry()


@frm_upd.update_frame
async def store_email_flow_password_change(dsrc: Source, email: str) -> Optional[str]:
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
