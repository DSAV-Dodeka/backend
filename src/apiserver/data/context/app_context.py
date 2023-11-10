from dataclasses import dataclass
from typing import Literal, Optional, Type

from sqlalchemy.ext.asyncio import AsyncConnection
from apiserver.data.source import get_conn
from datacontext.context import (
    Context,
    AbstractContexts,
    ContextError,
    ContextNotImpl,
    RIn,
    ROut,
    P,
    T_co,
)
from auth.core.model import SavedRegisterState
from auth.data.context import Contexts
from apiserver.data import Source
from apiserver.lib.model.entities import (
    ClassEvent,
    NewEvent,
    UserData,
    User,
    UserEvent,
    UserPointsNames,
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


class RankingContext(Context):
    @classmethod
    async def add_new_event(cls, dsrc: Source, new_event: NewEvent) -> None:
        raise ContextNotImpl()

    @classmethod
    async def context_most_recent_class_id_of_type(
        cls, dsrc: Source, rank_type: Literal["points", "training"]
    ) -> int:
        raise ContextNotImpl()

    @classmethod
    async def context_most_recent_class_points(
        cls, dsrc: Source, rank_type: Literal["points", "training"], is_admin: bool
    ) -> list[UserPointsNames]:
        raise ContextNotImpl()

    @classmethod
    async def sync_publish_ranking(cls, dsrc: Source, publish: bool) -> None:
        raise ContextNotImpl()

    @classmethod
    async def context_user_events_in_class(
        cls, dsrc: Source, user_id: str, class_id: int
    ) -> list[UserEvent]:
        raise ContextNotImpl()

    @classmethod
    async def context_events_in_class(
        cls, dsrc: Source, class_id: int
    ) -> list[ClassEvent]:
        raise ContextNotImpl()

    @classmethod
    async def context_get_event_users(
        cls, dsrc: Source, event_id: str
    ) -> list[UserPointsNames]:
        raise ContextNotImpl()


class AuthorizeAppContext(Context):
    @classmethod
    async def require_admin(cls, authorization: str, dsrc: Source) -> bool:
        raise ContextNotImpl()


class SourceContexts(AbstractContexts):
    register_ctx: RegisterAppContext
    update_ctx: UpdateContext
    rank_ctx: RankingContext
    authrz_ctx: AuthorizeAppContext

    def __init__(self) -> None:
        self.register_ctx = RegisterAppContext()
        self.update_ctx = UpdateContext()
        self.rank_ctx = RankingContext()
        self.authrz_ctx = AuthorizeAppContext()

    def context_from_type(self, registry_type: Type[Context]) -> Context:
        if registry_type is RegisterAppContext:
            return self.register_ctx
        elif registry_type is UpdateContext:
            return self.update_ctx
        elif registry_type is RankingContext:
            return self.rank_ctx
        elif registry_type is AuthorizeAppContext:
            return self.authrz_ctx

        raise ContextError("Type does not match any valid contexts!")


def conn_wrap(
    original_function: RIn[AsyncConnection, P, T_co]
) -> ROut[Source, P, T_co]:
    """Wraps original_function by getting a Connection from the Source object and providing that to the original
    function. Returns a function which has Source as its first argument, instead of AsyncConnection. Use this with
    `ctxlize_wrap`."""

    async def wrapped(replaced_arg: Source, *args: P.args, **kwargs: P.kwargs) -> T_co:
        async with get_conn(replaced_arg) as conn:
            return await original_function(conn, *args, **kwargs)

    return wrapped


@dataclass
class Code:
    auth_context: Contexts
    app_context: SourceContexts
