from dataclasses import dataclass, field
from typing import Type

from auth.core.model import (
    SavedState,
    FlowUser,
    AuthRequest,
    KeyState,
    IdInfo,
    AuthKeys,
    RefreshToken,
    SavedRegisterState,
)
from auth.data.schemad.entities import SavedRefreshToken
from auth.data.schemad.ops import SchemaOps
from auth.data.schemad.user import UserOps
from datacontext.context import (
    Context,
    create_context_impl,
    AbstractContexts,
    ContextError,
)
from store import Store


class LoginContext(Context):
    @classmethod
    async def get_apake_setup(cls, ctx: Context, store: Store) -> str: ...

    @classmethod
    async def get_user_auth_data(
        cls, ctx: Context, store: Store, user_ops: UserOps, login_mail: str
    ) -> tuple[str, str, str, str]: ...

    @classmethod
    async def store_auth_state(
        cls, ctx: Context, store: Store, auth_id: str, state: SavedState
    ) -> None: ...

    @classmethod
    async def get_state(
        cls, ctx: Context, store: Store, auth_id: str
    ) -> SavedState: ...

    @classmethod
    async def store_flow_user(
        cls, ctx: Context, store: Store, session_key: str, flow_user: FlowUser
    ) -> None: ...


class AuthorizeContext(Context):
    @classmethod
    async def store_auth_request(
        cls, ctx: Context, store: Store, auth_request: AuthRequest
    ): ...

    @classmethod
    async def get_auth_request(
        cls, ctx: Context, store: Store, flow_id: str
    ) -> AuthRequest: ...


class TokenContext(Context):
    @classmethod
    async def pop_flow_user(
        cls, ctx: Context, store: Store, authorization_code: str
    ) -> FlowUser: ...

    @classmethod
    async def get_auth_request(
        cls, ctx: Context, store: Store, flow_id: str
    ) -> AuthRequest: ...

    @classmethod
    async def get_keys(
        cls, ctx: Context, store: Store, key_state: KeyState
    ) -> AuthKeys: ...

    @classmethod
    async def get_id_info(
        cls, ctx: Context, store: Store, ops: SchemaOps, user_id: str
    ) -> IdInfo: ...

    @classmethod
    async def add_refresh_token(
        cls, ctx: Context, store: Store, ops: SchemaOps, refresh_save: SavedRefreshToken
    ) -> int: ...

    @classmethod
    async def get_saved_refresh(
        cls, ctx: Context, store: Store, ops: SchemaOps, old_refresh: RefreshToken
    ) -> SavedRefreshToken: ...

    @classmethod
    async def replace_refresh(
        cls,
        ctx: Context,
        store: Store,
        ops: SchemaOps,
        old_refresh_id: int,
        new_refresh_save: SavedRefreshToken,
    ) -> int: ...

    @classmethod
    async def delete_refresh_token(
        cls, ctx: Context, store: Store, ops: SchemaOps, family_id: str
    ) -> int: ...


class RegisterContext(Context):
    @classmethod
    async def get_apake_setup(cls, ctx: Context, store: Store) -> str: ...

    @classmethod
    async def store_auth_register_state(
        cls, ctx: Context, store: Store, user_id: str, state: SavedRegisterState
    ) -> str: ...


@dataclass
class Contexts(AbstractContexts):
    # Using this default factory makes sure that different instances of Context don't share ContextImpl's
    login_ctx: LoginContext = field(default_factory=create_context_impl)
    authorize_ctx: AuthorizeContext = field(default_factory=create_context_impl)
    token_ctx: TokenContext = field(default_factory=create_context_impl)
    register_ctx: RegisterContext = field(default_factory=create_context_impl)

    def context_from_type(self, registry_type: Type[Context]) -> Context:
        if registry_type is LoginContext:
            return self.login_ctx
        elif registry_type is AuthorizeContext:
            return self.authorize_ctx
        elif registry_type is TokenContext:
            return self.token_ctx
        elif registry_type is RegisterContext:
            return self.register_ctx

        raise ContextError("Type does not match any valid contexts!")
