from typing import Type
from auth.data.relational.refresh import RefreshOps

from auth.data.relational.user import UserOps, IdUserDataOps


class RelationOps:
    user: Type[UserOps]
    id_userdata: Type[IdUserDataOps]
    refresh: Type[RefreshOps]
