from dataclasses import dataclass
from typing import Type
from apiserver.data.api.refreshtoken import RefreshOps
from apiserver.data.api.user import UserOps
from apiserver.data.api.ud.userdata import UserDataOps
from auth.data.schemad.ops import SchemaOps as AuthSchemaOps


__all__ = ["OPS", "UserOps"]


@dataclass
class SchemaOps(AuthSchemaOps):
    user: Type[UserOps]
    userdata: Type[UserDataOps]
    refresh: Type[RefreshOps]


OPS = SchemaOps(user=UserOps, userdata=UserDataOps, refresh=RefreshOps)
