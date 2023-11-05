from dataclasses import dataclass, field
from typing import Optional, Type

from apiserver.data import Source
from apiserver.lib.model.entities import UserData, User
from auth.core.model import SavedRegisterState
from auth.data.context import Contexts
from datacontext.context import (
    Context,
    create_context_impl,
    AbstractContexts,
    ContextError,
)


class RegisterAppContext(Context):
    @classmethod
    async def get_registration(
        cls, ctx: Context, dsrc: Source, register_id: str
    ) -> tuple[UserData, User]: ...

    @classmethod
    async def get_register_state(
        cls, ctx: Context, dsrc: Source, auth_id: str
    ) -> SavedRegisterState: ...

    @classmethod
    async def check_userdata_register(
        cls,
        ctx: Context,
        dsrc: Source,
        register_id: str,
        request_email: str,
        saved_user_id: str,
    ) -> UserData: ...

    @classmethod
    async def save_registration(
        cls, ctx: Context, dsrc: Source, pw_file: str, new_userdata: UserData
    ) -> None: ...


class UpdateContext(Context):
    @classmethod
    async def store_email_flow_password_change(
        cls, ctx: Context, dsrc: Source, email: str
    ) -> Optional[str]: ...


@dataclass
class SourceContexts(AbstractContexts):
    register_ctx: RegisterAppContext = field(default_factory=create_context_impl)
    update_ctx: UpdateContext = field(default_factory=create_context_impl)

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
