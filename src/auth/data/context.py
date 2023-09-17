import inspect

from dataclasses import dataclass
from typing import Callable, Protocol

from auth.core.model import SavedState
from auth.data.schemad.user import UserOps
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


class LoginContextImpl:
    """By making an empty class, we ensure that it breaks if called without it being registered, instead of silently
    returning None."""

    pass


@dataclass
class Context:
    login_context: LoginContext = LoginContextImpl()


context = Context()


def login_context(arg):
    make_data_context(context.login_context, LoginContext, arg)

    return arg
