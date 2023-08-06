from auth.core.model import AuthRequest
from auth.core.util import random_time_hash_hex
from auth.data import DataSource
import auth.store
from auth.store.source import StoreSource


async def store_auth_request(dsrc: DataSource, auth_request: AuthRequest) -> str:
    """Persist the auth request in some way, so it can later be re-used. Returns a string that can be added as
    an url query parameter to later retrieve this information."""
    if isinstance(dsrc, StoreSource):
        flow_id = random_time_hash_hex()

        await auth.store.trs.auth.store_auth_request(dsrc, flow_id, auth_request)

        return flow_id


async def get_auth_request(dsrc: DataSource, retrieval_query: str) -> AuthRequest:
    if isinstance(dsrc, StoreSource):
        flow_id = retrieval_query

        return await auth.store.trs.auth.get_auth_request(dsrc, flow_id)
