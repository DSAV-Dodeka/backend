import inspect
from dataclasses import dataclass, field
from typing import Callable, Protocol

from apiserver.data import Source
from apiserver.lib.model.entities import UserData, User
from auth.core.model import SavedRegisterState
from auth.data.context import Context


class FrameError(Exception):
    pass


def make_source_frame(frame_inst, frame_protocol, func: Callable):
    if not hasattr(frame_protocol, func.__name__):
        raise FrameError(
            f"Have you forgotten to write a protocol for function {func!s}?"
        )

    old_func = getattr(frame_protocol, func.__name__)

    # We compare the type annotations
    old_anno = inspect.get_annotations(old_func)
    new_anno = inspect.get_annotations(func)

    if old_anno != new_anno:
        raise FrameError(
            f"Protocol annotation:\n {old_anno!s}\n does not equal function"
            f" annotation:\n {new_anno!s}!"
        )

    setattr(frame_inst, func.__name__, func)


class RegisterFrame(Protocol):
    @classmethod
    async def get_registration(
        cls, dsrc: Source, register_id: str
    ) -> tuple[UserData, User]:
        ...

    @classmethod
    async def get_register_state(cls, dsrc: Source, auth_id: str) -> SavedRegisterState:
        ...

    @classmethod
    async def check_userdata_register(
        cls, dsrc: Source, register_id: str, request_email: str, saved_user_id: str
    ) -> UserData:
        """Must also ensure request_email and saved_user_id match the userdata."""
        ...

    @classmethod
    async def save_registration(
        cls, dsrc: Source, pw_file: str, new_userdata: UserData
    ) -> None:
        """Assumes the new_userdata has the same user_id and email as the registration starter."""
        ...


class FrameImpl:
    """By making an empty class, we ensure that it breaks if called without it being registered, instead of silently
    returning None."""

    pass


def create_frame_impl() -> FrameImpl:
    return FrameImpl()


default_impl = field(default_factory=create_frame_impl)


@dataclass
class SourceFrame:
    # Using this default factory makes sure that different instances of Frame don't share FrameImpl's
    register_frm: RegisterFrame = default_impl


source_frame = SourceFrame()


# Decorators, apply these to the actual function definitions
# These are also useful to quickly find the functions


def register_frame(arg):
    make_source_frame(source_frame.register_frm, RegisterFrame, arg)

    return arg


@dataclass
class Code:
    context: Context
    frame: SourceFrame
