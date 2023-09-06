from apiserver.data.api.refreshtoken import RefreshOps
from apiserver.data.api.user import UserOps
from apiserver.data.api.ud.userdata import UserDataOps
from auth.data.schemad.ops import SchemaOps


__all__ = ["OPS"]


OPS = SchemaOps(user=UserOps, userdata=UserDataOps, refresh=RefreshOps)
