from typing import Type

from auth.core.model import (
    SavedState,
    FlowUser,
    AuthRequest,
    KeyState,
    AuthKeys,
    RefreshToken,
    SavedRegisterState,
)
from auth.data.relational.entities import SavedRefreshToken
from auth.data.relational.ops import RelationOps
from auth.data.relational.user import IdUserData, UserOps
from datacontext.context import (
    Context,
    AbstractContexts,
    ContextError,
    ContextNotImpl,
)
from store import Store


class LoginContext(Context):
    @classmethod
    async def get_apake_setup(cls, store: Store) -> str:
        raise ContextNotImpl()

    @classmethod
    async def get_user_auth_data(
        cls, store: Store, user_ops: UserOps, login_mail: str
    ) -> tuple[str, str, str, str]:
        raise ContextNotImpl()

    @classmethod
    async def store_auth_state(
        cls, store: Store, auth_id: str, state: SavedState
    ) -> None:
        raise ContextNotImpl()

    @classmethod
    async def get_state(cls, store: Store, auth_id: str) -> SavedState:
        raise ContextNotImpl()

    @classmethod
    async def store_flow_user(
        cls, store: Store, session_key: str, flow_user: FlowUser
    ) -> None:
        raise ContextNotImpl()

    @classmethod
    async def pop_flow_user(cls, store: Store, authorization_code: str) -> FlowUser:
        raise ContextNotImpl()


class AuthorizeContext(Context):
    @classmethod
    async def store_auth_request(cls, store: Store, auth_request: AuthRequest) -> str:
        raise ContextNotImpl()

    @classmethod
    async def get_auth_request(cls, store: Store, flow_id: str) -> AuthRequest:
        raise ContextNotImpl()


class TokenContext(Context):
    @classmethod
    async def pop_flow_user(cls, store: Store, authorization_code: str) -> FlowUser:
        raise ContextNotImpl()

    @classmethod
    async def get_auth_request(cls, store: Store, flow_id: str) -> AuthRequest:
        raise ContextNotImpl()

    @classmethod
    async def get_keys(cls, store: Store, key_state: KeyState) -> AuthKeys:
        raise ContextNotImpl()

    @classmethod
    async def get_id_userdata(
        cls, store: Store, ops: RelationOps, user_id: str
    ) -> IdUserData:
        raise ContextNotImpl()

    @classmethod
    async def add_refresh_token(
        cls, store: Store, ops: RelationOps, refresh_save: SavedRefreshToken
    ) -> int:
        raise ContextNotImpl()

    @classmethod
    async def get_saved_refresh(
        cls, store: Store, ops: RelationOps, old_refresh: RefreshToken
    ) -> SavedRefreshToken:
        raise ContextNotImpl()

    @classmethod
    async def replace_refresh(
        cls,
        store: Store,
        ops: RelationOps,
        old_refresh_id: int,
        new_refresh_save: SavedRefreshToken,
    ) -> int:
        raise ContextNotImpl()

    @classmethod
    async def delete_refresh_token(
        cls, store: Store, ops: RelationOps, family_id: str
    ) -> int:
        raise ContextNotImpl()


class RegisterContext(Context):
    @classmethod
    async def get_apake_setup(cls, store: Store) -> str:
        raise ContextNotImpl()

    @classmethod
    async def store_auth_register_state(
        cls, store: Store, user_id: str, state: SavedRegisterState
    ) -> str:
        raise ContextNotImpl()


class Contexts(AbstractContexts):
    # Using this default factory makes sure that different instances of Context don't share ContextImpl's
    login_ctx: LoginContext
    authorize_ctx: AuthorizeContext
    token_ctx: TokenContext
    register_ctx: RegisterContext

    def __init__(self) -> None:
        self.login_ctx = LoginContext()
        self.authorize_ctx = AuthorizeContext()
        self.token_ctx = TokenContext()
        self.register_ctx = RegisterContext()

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
