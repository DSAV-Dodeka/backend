from abc import abstractmethod
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
    AbstractContexts,
    ContextError,
)
from store import Store


class LoginContext(Context):
    @classmethod
    @abstractmethod
    async def get_apake_setup(cls, store: Store) -> str: ...

    @classmethod
    @abstractmethod
    async def get_user_auth_data(
        cls, store: Store, user_ops: UserOps, login_mail: str
    ) -> tuple[str, str, str, str]: ...

    @classmethod
    @abstractmethod
    async def store_auth_state(
        cls, store: Store, auth_id: str, state: SavedState
    ) -> None: ...

    @classmethod
    @abstractmethod
    async def get_state(cls, store: Store, auth_id: str) -> SavedState: ...

    @classmethod
    @abstractmethod
    async def store_flow_user(
        cls, store: Store, session_key: str, flow_user: FlowUser
    ) -> None: ...


class AuthorizeContext(Context):
    @classmethod
    @abstractmethod
    async def store_auth_request(
        cls, store: Store, auth_request: AuthRequest
    ) -> None: ...

    @classmethod
    @abstractmethod
    async def get_auth_request(cls, store: Store, flow_id: str) -> AuthRequest: ...


class TokenContext(Context):
    @classmethod
    @abstractmethod
    async def pop_flow_user(cls, store: Store, authorization_code: str) -> FlowUser: ...

    @classmethod
    @abstractmethod
    async def get_auth_request(cls, store: Store, flow_id: str) -> AuthRequest: ...

    @classmethod
    @abstractmethod
    async def get_keys(cls, store: Store, key_state: KeyState) -> AuthKeys: ...

    @classmethod
    @abstractmethod
    async def get_id_info(
        cls, store: Store, ops: SchemaOps, user_id: str
    ) -> IdInfo: ...

    @classmethod
    @abstractmethod
    async def add_refresh_token(
        cls, store: Store, ops: SchemaOps, refresh_save: SavedRefreshToken
    ) -> int: ...

    @classmethod
    @abstractmethod
    async def get_saved_refresh(
        cls, store: Store, ops: SchemaOps, old_refresh: RefreshToken
    ) -> SavedRefreshToken: ...

    @classmethod
    @abstractmethod
    async def replace_refresh(
        cls,
        store: Store,
        ops: SchemaOps,
        old_refresh_id: int,
        new_refresh_save: SavedRefreshToken,
    ) -> int: ...

    @classmethod
    @abstractmethod
    async def delete_refresh_token(
        cls, store: Store, ops: SchemaOps, family_id: str
    ) -> int: ...


class RegisterContext(Context):
    @classmethod
    @abstractmethod
    async def get_apake_setup(cls, store: Store) -> str: ...

    @classmethod
    @abstractmethod
    async def store_auth_register_state(
        cls, store: Store, user_id: str, state: SavedRegisterState
    ) -> str: ...


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
