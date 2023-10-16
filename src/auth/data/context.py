import inspect

from dataclasses import dataclass, field
from typing import Callable, Protocol

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
from store import Store


class ContextError(Exception):
    pass


def make_data_context(context_inst, context_protocol, func: Callable):
    # We check if the target protocol has a name of that function
    if not hasattr(context_protocol, func.__name__):
        raise ContextError(
            f"Have you forgotten to write a protocol for function {func!s}?"
        )
    # We get the protocol's function definition
    old_func = getattr(context_protocol, func.__name__)

    # We compare the type annotations
    old_anno = inspect.get_annotations(old_func)
    new_anno = inspect.get_annotations(func)

    if old_anno != new_anno:
        raise ContextError(
            f"Protocol annotation:\n {old_anno!s}\n does not equal function"
            f" annotation:\n {new_anno!s}!"
        )

    # We add the function to the context instance
    setattr(context_inst, func.__name__, func)


class LoginContext(Protocol):
    @classmethod
    async def get_apake_setup(cls, store: Store) -> str:
        ...

    @classmethod
    async def get_user_auth_data(
        cls, store: Store, user_ops: UserOps, login_mail: str
    ) -> tuple[str, str, str, str]:
        ...

    @classmethod
    async def store_auth_state(
        cls, store: Store, auth_id: str, state: SavedState
    ) -> None:
        ...

    @classmethod
    async def get_state(cls, store: Store, auth_id: str) -> SavedState:
        ...

    @classmethod
    async def store_flow_user(
        cls, store: Store, session_key: str, flow_user: FlowUser
    ) -> None:
        ...


class AuthorizeContext(Protocol):
    @classmethod
    async def store_auth_request(cls, store: Store, auth_request: AuthRequest):
        ...

    @classmethod
    async def get_auth_request(cls, store: Store, flow_id: str) -> AuthRequest:
        ...


class TokenContext(Protocol):
    @classmethod
    async def pop_flow_user(cls, store: Store, authorization_code: str) -> FlowUser:
        ...

    @classmethod
    async def get_auth_request(cls, store: Store, flow_id: str) -> AuthRequest:
        ...

    @classmethod
    async def get_keys(cls, store: Store, key_state: KeyState) -> AuthKeys:
        ...

    @classmethod
    async def get_id_info(cls, store: Store, ops: SchemaOps, user_id: str) -> IdInfo:
        ...

    @classmethod
    async def add_refresh_token(
        cls, store: Store, ops: SchemaOps, refresh_save: SavedRefreshToken
    ) -> int:
        ...

    @classmethod
    async def get_saved_refresh(
        cls, store: Store, ops: SchemaOps, old_refresh: RefreshToken
    ) -> SavedRefreshToken:
        ...

    @classmethod
    async def replace_refresh(
        cls,
        store: Store,
        ops: SchemaOps,
        old_refresh_id: int,
        new_refresh_save: SavedRefreshToken,
    ) -> int:
        ...

    @classmethod
    async def delete_refresh_token(
        cls, store: Store, ops: SchemaOps, family_id: str
    ) -> int:
        ...


class RegisterContext(Protocol):
    @classmethod
    async def get_apake_setup(cls, store: Store) -> str:
        ...

    @classmethod
    async def store_auth_register_state(
        cls, store: Store, user_id: str, state: SavedRegisterState
    ) -> str:
        ...


class ContextImpl:
    """By making an empty class, we ensure that it breaks if called without it being registered, instead of silently
    returning None."""

    pass


def create_context_impl() -> ContextImpl:
    return ContextImpl()


def include_contexts(funcs: list[Callable], context_inst, context_protocol):
    for func in funcs:
        make_data_context(context_inst, context_protocol, func)


@dataclass
class ContextRegistry:
    login_funcs: list[Callable] = field(default_factory=list)
    authorize_funcs: list[Callable] = field(default_factory=list)
    token_funcs: list[Callable] = field(default_factory=list)
    register_funcs: list[Callable] = field(default_factory=list)

    # These are all decorators and are useful to find the actual functions
    def login_context(self, func):
        self.login_funcs.append(func)

        return func

    def authorize_context(self, func):
        self.authorize_funcs.append(func)

        return func

    def token_context(self, func):
        self.token_funcs.append(func)

        return func

    def register_context(self, func):
        self.register_funcs.append(func)

        return func


@dataclass
class Context:
    # Using this default factory makes sure that different instances of Context don't share ContextImpl's
    login_ctx: LoginContext = field(default_factory=create_context_impl)
    authorize_ctx: AuthorizeContext = field(default_factory=create_context_impl)
    token_ctx: TokenContext = field(default_factory=create_context_impl)
    register_ctx: RegisterContext = field(default_factory=create_context_impl)

    def include_registry(self, registry: ContextRegistry):
        include_contexts(registry.login_funcs, self.login_ctx, LoginContext)
        include_contexts(registry.authorize_funcs, self.authorize_ctx, AuthorizeContext)
        include_contexts(registry.token_funcs, self.token_ctx, TokenContext)
        include_contexts(registry.register_funcs, self.register_ctx, RegisterContext)
