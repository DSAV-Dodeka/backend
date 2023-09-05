from apiserver.data.api.refreshtoken import RefreshOps
from apiserver.data.api.user import UserOps, UserDataOps
from auth.data.schemad.ops import SchemaOps


__all__ = ["SCHEMA"]


SCHEMA = SchemaOps(user=UserOps, userdata=UserDataOps, refresh=RefreshOps)
