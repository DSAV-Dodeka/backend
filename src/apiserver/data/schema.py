from dataclasses import dataclass
from typing import Type
from apiserver.data.api.refreshtoken import RefreshOps
from apiserver.data.api.user import UserOps
from apiserver.data.api.ud.userdata import IdUserDataOps
from auth.data.relational.ops import RelationOps as AuthRelationOps


__all__ = ["OPS", "UserOps"]


@dataclass
class SchemaOps(AuthRelationOps):
    user: Type[UserOps]
    id_userdata: Type[IdUserDataOps]
    refresh: Type[RefreshOps]


OPS = SchemaOps(user=UserOps, id_userdata=IdUserDataOps, refresh=RefreshOps)
