from typing import Optional

from apiserver.define.entities import SignedUp
from apiserver.data.source import Source, DataError
from apiserver.data.use import retrieve_by_id, retrieve_by_unique, insert
from apiserver.db import SIGNEDUP_TABLE
from apiserver.db.model import SU_FIRSTNAME, SU_LASTNAME, SU_EMAIL, SU_PHONE
from apiserver.db.ops import DbError


__all__ = ['get_signedup_by_email', 'insert_su_row']


def parse_signedup(signedup_dict: Optional[dict]) -> SignedUp:
    if signedup_dict is None:
        raise DataError("User does not exist.", "signedup_empty")
    return SignedUp.parse_obj(signedup_dict)


async def get_signedup_by_email(dsrc: Source, email: str) -> SignedUp:
    signedup_row = await retrieve_by_unique(dsrc, SIGNEDUP_TABLE, SU_EMAIL, email)
    return parse_signedup(signedup_row)


async def insert_su_row(dsrc: Source, su_row: dict):
    try:
        result = await insert(dsrc, SIGNEDUP_TABLE, su_row)
    except DbError as e:
        raise DataError(f"{e.err_desc} from internal: {e.err_internal}", e.debug_key)
    return result
