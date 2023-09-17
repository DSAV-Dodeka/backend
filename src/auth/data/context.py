from dataclasses import dataclass
from typing import Callable, Protocol

from apiserver.data.api.user import UserOps
from auth.core.model import SavedState
from store import Store


def make_data_context(context_protocol, func: Callable):
    setattr(context_protocol, func.__name__, func)


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


@dataclass
class Context:
    login_context = LoginContext


context = Context()


def login_context(arg):
    make_data_context(context.login_context, arg)

    return arg
