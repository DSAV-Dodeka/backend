from dataclasses import dataclass
from typing import Type

from auth.data.schemad.refresh import RefreshOps
from auth.data.schemad.user import UserOps, UserDataOps


@dataclass
class SchemaOps:
    user: Type[UserOps]
    userdata: Type[UserDataOps]
    refresh: Type[RefreshOps]
