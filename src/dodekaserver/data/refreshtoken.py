from typing import Optional

from dodekaserver.data.source import Source, DataError, Gateway
from dodekaserver.define.entities import SavedRefreshToken
from dodekaserver.db.tdg.refreshtoken import query_refresh_by_id, query_delete_family, query_refresh_transaction


def parse_refresh(refresh_dict: Optional[dict]) -> SavedRefreshToken:
    if refresh_dict is None:
        raise DataError("Refresh Token does not exist.", "refresh_empty")
    return SavedRefreshToken.parse_obj(refresh_dict)


async def get_refresh_by_id(dsrc: Source, id_int: int) -> SavedRefreshToken:
    return await query_refresh_by_id(dsrc.gateway, id_int)


async def delete_family(dsrc: Source, family_id: str) -> SavedRefreshToken:
    return await query_delete_family(dsrc.gateway, family_id)


async def refresh_transaction(dsrc: Source, id_int_delete: int, new_refresh: SavedRefreshToken) -> int:
    return await query_refresh_transaction(dsrc.gateway, id_int_delete, new_refresh)
