import abc
import inspect

from dataclasses import dataclass, field
from typing import Callable, Type

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


class Context:
    dont_replace: bool = False


class DontReplaceContext(Context):
    dont_replace: bool = True


def make_data_context(
    context_inst: Context, context_protocol: Type[Context], func: Callable
):
    """This function is called for each registration (which happens through decorators) and it sets the dependency
    container function (which only has a stub implementation) to the actual implementation. It performs a few checks
    to ensure the stub matches the target function to avoid mistakes."""
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
            f"Protocol annotation for func {func.__name__}:\n {old_anno!s}\n does not"
            f" equal function annotation:\n {new_anno!s}!"
        )

    # We add the function to the context instance
    setattr(context_inst, func.__name__, func)


class ContextImpl(Context):
    """By making an empty class, we ensure that it breaks if called without it being registered, instead of silently
    returning None."""

    pass


def create_context_impl() -> ContextImpl:
    return ContextImpl()


def replace_context(func):
    """This function creates the replacement function by looking up the function name in the dependency container. It
    doesn't alter any behavior, as it simply calls the implementing function."""

    def replace(ctx: Context, *args, **kwargs):
        if ctx.dont_replace:
            return func(ctx, *args, **kwargs)

        replace_func = getattr(ctx, func.__name__)
        return replace_func(ctx, *args, **kwargs)

    return replace


@dataclass
class ContextRegistry:
    """This is not the global registry, but a simple container that provides the function decorator/registration
    functionality. You should define one for each file that contains functions."""

    funcs: list[tuple[Callable, Type[Context]]] = field(default_factory=list)

    def register(self, registry_type: Type[Context]):
        """This is the decorator that can be used to register implementations. It adds the function to the local
        registry object, which then needs to registered to the correct context instance by some global registry.
        The registry type should be a class that exists in the application's global contexts.
        """

        def decorator(func):
            # TODO think if do a check so this is not always called
            self.funcs.append((func, registry_type))

            return replace_context(func)

        return decorator

    def register_multiple(self, registry_types: list[Type[Context]]):
        # We need register_multiple because otherwise we will apply a decorator to the changed function
        # In that case the name and annotations are no longer correct

        def decorator(func):
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

    def include_registry(self, registry: ContextRegistry):
        for func, registry_type in registry.funcs:
            make_data_context(
                self.context_from_type(registry_type), registry_type, func
            )
