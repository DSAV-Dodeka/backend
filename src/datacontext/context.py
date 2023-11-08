import abc
import inspect

from dataclasses import dataclass, field
from typing import (
    Any,
    Callable,
    Concatenate,
    Coroutine,
    Generic,
    Protocol,
    Type,
    TypeAlias,
    TypeVar,
    ParamSpec,
)

"""
This module contains boilerplate for achieving dependency injection for functions calling the database. Dependency
injection is a useful pattern, both in functional and OO programming. We use it primarily to make testing easier,
because we can easily define our own object that works with a simple mock dict instead of the real database.

We do use some advanced Python functions, particularly decorators, to make it easier to register which functions we
want to be replaceable.

Some libraries exist that do this, but they are generally more object-oriented, and in our case we want to still
be able to define top-level functions to make it clear what the main implementation is. Some more functional ones
(like 'returns') are not as DX-friendly or too complex. This is designed to be a simple solution.
"""


class ContextError(Exception):
    pass


class ContextNotImpl(ContextError):
    def __init__(self) -> None:
        super().__init__(
            "No implementation was registered for this context stub method!"
        )


class Context:
    dont_replace: bool = False


class DontReplaceContext(Context):
    dont_replace: bool = True


def make_data_context(
    context_inst: Context, context_type: Type[Context], func: Callable[..., Any]
) -> None:
    """This function is called for each registration (which happens through decorators) and it sets the dependency
    container function (which only has a stub implementation) to the actual implementation. It performs a few checks
    to ensure the stub matches the target function to avoid mistakes."""
    # We check if the target protocol has a name of that function
    if not hasattr(context_type, func.__name__):
        raise ContextError(
            f"Have you forgotten to write a context stub for function {func!s}?"
        )
    # We get the context's function definition
    type_func = getattr(context_type, func.__name__)

    # We compare the type annotations
    type_anno = inspect.get_annotations(type_func)
    impl_anno = inspect.get_annotations(func)

    if type_anno != impl_anno:
        raise ContextError(
            f"Context stub annotation for func {func.__name__}:\n {type_anno!s}\n does"
            f" not equal function implmentation annotation:\n {impl_anno!s}!"
        )

    # We add the function to the context instance
    setattr(context_inst, func.__name__, func)


class ContextImpl(Context):
    """By making an empty class, we ensure that it breaks if called without it being registered, instead of silently
    returning None."""

    pass


C = TypeVar("C", bound=Context)


def create_context_impl(context: Type[C]) -> C:
    return ContextImpl()  # type: ignore


T_co = TypeVar("T_co", covariant=True)
P = ParamSpec("P")


class ContextCallable(Protocol, Generic[P, T_co]):
    def __call__(self, ctx: Context, *args: P.args, **kwargs: P.kwargs) -> T_co: ...


def replace_context(func: Callable[P, T_co]) -> ContextCallable[P, T_co]:
    """This function creates the replacement function by looking up the function name in the dependency container. It
    doesn't alter any behavior, as it simply calls the implementing function."""

    def replace(ctx: Context, *args: P.args, **kwargs: P.kwargs) -> T_co:
        if ctx.dont_replace:
            return func(*args, **kwargs)

        replace_func: Callable[P, T_co] = getattr(ctx, func.__name__)
        return replace_func(*args, **kwargs)

    return replace


class WrapContext(Context):
    pass


R_out_contra = TypeVar("R_out_contra", contravariant=True)
R_in_contra = TypeVar("R_in_contra", contravariant=True)


class ContextWrapCallable(Protocol, Generic[R_in_contra, P, T_co]):
    def __call__(
        self, ctx: WrapContext, r: R_in_contra, *args: P.args, **kwargs: P.kwargs
    ) -> Coroutine[Any, Any, T_co]: ...


RIn: TypeAlias = Callable[Concatenate[R_in_contra, P], Coroutine[Any, Any, T_co]]


class ROut(Protocol, Generic[R_out_contra, P, T_co]):
    def __call__(
        self, r: R_out_contra, *args: P.args, **kwargs: P.kwargs
    ) -> Coroutine[Any, Any, T_co]: ...


Wrapper: TypeAlias = Callable[[RIn[R_in_contra, P, T_co]], ROut[R_out_contra, P, T_co]]


def ctxlize(
    c: RIn[R_in_contra, P, T_co],
    w: Callable[[RIn[R_in_contra, P, T_co]], ROut[R_out_contra, P, T_co]],
) -> ContextWrapCallable[R_out_contra, P, T_co]:
    def ctx_callable(
        ctx: WrapContext, r: R_out_contra, *args: P.args, **kwargs: P.kwargs
    ) -> Coroutine[Any, Any, T_co]:
        if not ctx.dont_replace and hasattr(ctx, c.__name__):
            replaced_f: ROut[R_out_contra, P, T_co] = getattr(ctx, c.__name__)
            return replaced_f(r, *args, **kwargs)

        new_f = w(c)
        return new_f(r, *args, **kwargs)

    return ctx_callable


@dataclass
class ContextRegistry:
    """This is not the global registry, but a simple container that provides the function decorator/registration
    functionality. You should define one for each file that contains functions."""

    funcs: list[tuple[Callable[..., Any], Type[Context]]] = field(default_factory=list)

    def register(
        self, registry_type: Type[Context]
    ) -> Callable[[Callable[P, T_co]], ContextCallable[P, T_co]]:
        """This is the decorator that can be used to register implementations. It adds the function to the local
        registry object, which then needs to registered to the correct context instance by some global registry.
        The registry type should be a class that exists in the application's global contexts.
        """

        def decorator(func: Callable[P, T_co]) -> ContextCallable[P, T_co]:
            # TODO think if do a check so this is not always called
            self.funcs.append((func, registry_type))

            return replace_context(func)

        return decorator

    def register_multiple(
        self, registry_types: list[Type[Context]]
    ) -> Callable[[Callable[P, T_co]], ContextCallable[P, T_co]]:
        # We need register_multiple because otherwise we will apply a decorator to the changed function
        # In that case the name and annotations are no longer correct

        def decorator(func: Callable[P, T_co]) -> ContextCallable[P, T_co]:
            for r in registry_types:
                self.funcs.append((func, r))

            return replace_context(func)

        return decorator


class AbstractContexts(abc.ABC):
    """This should be used as the application's global registry. It is recommended to define the different context
    containers as class attributes and define them as `field(default_factory=create_context_impl)` so they are
    correctly instantiated. You should define an implementation for `context_from_type`, which in the simplest case
    just matches the type to teh correct class attribute (the actual context instance). Then, call `include_registry`
    with every ContextRegistry at application startup, or when running tests."""

    @abc.abstractmethod
    def context_from_type(self, registry_type: Type[Context]) -> Context: ...

    def include_registry(self, registry: ContextRegistry) -> None:
        for func, registry_type in registry.funcs:
            make_data_context(
                self.context_from_type(registry_type), registry_type, func
            )
