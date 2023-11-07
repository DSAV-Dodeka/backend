from dataclasses import dataclass
from typing import Optional, Type

from apiserver.data import Source
from apiserver.lib.model.entities import UserData, User
from auth.core.model import SavedRegisterState
from auth.data.context import Contexts
from datacontext.context import (
    Context,
    AbstractContexts,
    ContextError,
    ContextNotImpl,
)


class RegisterAppContext(Context):
    @classmethod
    async def get_registration(
        cls, dsrc: Source, register_id: str
    ) -> tuple[UserData, User]:
        raise ContextNotImpl()

    @classmethod
    async def get_register_state(cls, dsrc: Source, auth_id: str) -> SavedRegisterState:
        raise ContextNotImpl()

    @classmethod
    async def check_userdata_register(
        cls,
        dsrc: Source,
        register_id: str,
        request_email: str,
        saved_user_id: str,
    ) -> UserData:
        raise ContextNotImpl()

    @classmethod
    async def save_registration(
        cls, dsrc: Source, pw_file: str, new_userdata: UserData
    ) -> None:
        raise ContextNotImpl()


class UpdateContext(Context):
    @classmethod
    async def store_email_flow_password_change(
        cls, dsrc: Source, email: str
    ) -> Optional[str]:
        raise ContextNotImpl()


class SourceContexts(AbstractContexts):
    register_ctx: RegisterAppContext
    update_ctx: UpdateContext

    def __init__(self) -> None:
        self.register_ctx = RegisterAppContext()
        self.update_ctx = UpdateContext()

    def context_from_type(self, registry_type: Type[Context]) -> Context:
        if registry_type is RegisterAppContext:
            return self.register_ctx
        elif registry_type is UpdateContext:
            return self.update_ctx

        raise ContextError("Type does not match any valid contexts!")


@dataclass
class Code:
    auth_context: Contexts
    app_context: SourceContexts
