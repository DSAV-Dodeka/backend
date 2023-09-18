import inspect

from dataclasses import dataclass
from typing import Callable, Protocol

from auth.core.model import SavedState, FlowUser, AuthRequest, KeyState, IdInfo
from auth.data.schemad.entities import SavedRefreshToken
from auth.data.schemad.ops import SchemaOps
from auth.data.schemad.user import UserOps
from auth.hazmat.structs import SymmetricKey, PEMPrivateKey
from store import Store


class ContextError(Exception):
    pass


def make_data_context(context_inst, context_protocol, func: Callable):
    if not hasattr(context_protocol, func.__name__):
        raise ContextError(
            f"Have you forgotten to write a protocol for function {func!s}?"
        )

    old_func = getattr(context_protocol, func.__name__)

    # We compare the type annotations
    old_anno = inspect.get_annotations(old_func)
    new_anno = inspect.get_annotations(func)

    if old_anno != new_anno:
        raise ContextError(
            f"Protocol annotation:\n {old_anno!s}\n does not equal function"
            f" annotation:\n {new_anno!s}!"
        )

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
    async def get_keys(
        cls, store: Store, key_state: KeyState
    ) -> tuple[SymmetricKey, SymmetricKey, PEMPrivateKey]:
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
        cls, store: Store, ops: SchemaOps, old_refresh
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


class ContextImpl:
    """By making an empty class, we ensure that it breaks if called without it being registered, instead of silently
    returning None."""

    pass


@dataclass
class Context:
    login_ctx: LoginContext = ContextImpl()
    authorize_ctx: AuthorizeContext = ContextImpl()
    token_ctx: TokenContext = ContextImpl()


context = Context()


# Decorators, apply these to the actual function definitions
# These are also useful to quickly find the functions


def login_context(arg):
    make_data_context(context.login_ctx, LoginContext, arg)

    return arg


def authorize_context(arg):
    make_data_context(context.authorize_ctx, AuthorizeContext, arg)

    return arg


def token_context(arg):
    make_data_context(context.token_ctx, TokenContext, arg)

    return arg