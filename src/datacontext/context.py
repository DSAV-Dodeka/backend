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

Short tutorial:
- Define what different registry types you want. Maybe you want just one, or maybe one for login, one for onboarding,
  or similar. For each one, subclass the Context class and add function stubs for each function you want to be able
  to override.
- Write the implementations for the function stubs as top-level functions in your application. Then, in each file,
  instantiate a ContextRegistry and use its `register` function as a decorator on the context functions. This will
  save them inside the ContextRegistry.
- Subclass AbstractContexts and populate it with every specific registry type you want. E.g. one for login, one for
  onboarding or similar.
- Call the `include_registry` function with the different ContextRegistry's you instantiated. Make sure the
  AbsractContexts subclass is globally accessible in each consuming location.
- Simply call the original top-level function, providing the correct Context as its first argument. By overriding
  the Context class in some way, you can easily use it to override the call to your original function.
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
    if not isinstance(context_inst, context_type):
        raise ContextError(
            f"Context inst {context_inst} is not of the same type as the registry"
            f" {context_type}!"
        )

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
    """Creates the replacement function by looking up the function name in the dependency container. It
    doesn't alter any behavior, as it simply calls the implementing function."""

    def replace(ctx: Context, *args: P.args, **kwargs: P.kwargs) -> T_co:
        if ctx.dont_replace:
            return func(*args, **kwargs)

        replace_func: Callable[P, T_co] = getattr(ctx, func.__name__)
        return replace_func(*args, **kwargs)

    return replace


@dataclass
class ContextRegistry:
    """This is not the global registry, but a simple container that provides the function decorator/registration
    functionality. You should define one for each file that contains functions."""

    funcs: list[tuple[Callable[..., Any], Type[Context]]] = field(default_factory=list)

    def register(
        self, registry_type: Type[Context]
    ) -> Callable[[Callable[P, T_co]], ContextCallable[P, T_co]]:
        """Registers implementations for context functions. Use it as a decorator. It adds the function to the local
        registry object, which then needs to registered to the correct context instance by some global registry.
        The registry type should be a class that exists in the application's global contexts.

        Args:
            registry_type: The Context subclass containing the stub for the function you are registering.
        """

        def decorator(func: Callable[P, T_co]) -> ContextCallable[P, T_co]:
            # TODO think if do a check so this is not always called
            self.funcs.append((func, registry_type))

            return replace_context(func)

        return decorator

    def register_multiple(
        self, registry_types: list[Type[Context]]
    ) -> Callable[[Callable[P, T_co]], ContextCallable[P, T_co]]:
        """Registers multiple registry types at once for a single function. Use this instead of multiple decorators, as
        that won't work. See `register` for more details."""
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


# Everything below should only be used for very simple functions that are exposed directly to consumers, i.e. some
# function that loads something from a database and then returns it without performing any kind of logic.

# Type variables for the argument that is to be replaced
# Contravariant is  just for correctness, you would never want to subclass any of the functions they are used for.
R_out_contra = TypeVar("R_out_contra", contravariant=True)
R_in_contra = TypeVar("R_in_contra", contravariant=True)


class ContextWrapCallable(Protocol, Generic[R_in_contra, P, T_co]):
    """Result type of calling `ctxlize`. This is used in place of a Callable to ensure the argument names are
    correct."""

    def __call__(
        self, ctx: Context, replaced_arg: R_in_contra, *args: P.args, **kwargs: P.kwargs
    ) -> Coroutine[Any, Any, T_co]: ...


# Async function that will be wrapped and to which a context parameter will be added in `ctxlize`
# Its first argument will be transformed by the wrapper function.
RIn: TypeAlias = Callable[Concatenate[R_in_contra, P], Coroutine[Any, Any, T_co]]


class ROut(Protocol, Generic[R_out_contra, P, T_co]):
    """Result type of the wrapper function. This is the same as RIn, but its first argument is different.."""

    def __call__(
        self, replaced_arg: R_out_contra, *args: P.args, **kwargs: P.kwargs
    ) -> Coroutine[Any, Any, T_co]: ...


# Function that transforms RIn to ROut
Wrapper: TypeAlias = Callable[[RIn[R_in_contra, P, T_co]], ROut[R_out_contra, P, T_co]]


def ctxlize_wrap(
    original_function: RIn[R_in_contra, P, T_co],
    wrapper_function: Callable[
        [RIn[R_in_contra, P, T_co]], ROut[R_out_contra, P, T_co]
    ],
) -> ContextWrapCallable[R_out_contra, P, T_co]:
    """Takes a function, wraps it to replace the first argument and adds a context argument. Alternative to defining
    a context function and adding a stub to a context class. This is useful if the function simply wraps another
    function and provides no other functionality, which would make the added work and additional layer rather
    unnecessary. Note that the functions are assumed to be async functions and the function is wrapped only if the
    provided context does not have a replacement function.

    An example of why the wrapper function is necessary is to extract a Connection from an Engine object.

    Args:
        original_function: function you want to call with a context object containing a potential replacement
        wrapper_function: function used to replace the first argument and apply additional logic to the original
            function, taking in the original function as an argument and returning a new function.

    Returns:
        A new function that takes a Context as a first argument and then the replaced argument from the wrap
        function.
    """

    def ctx_callable(
        ctx: Context, replaced_arg: R_out_contra, *args: P.args, **kwargs: P.kwargs
    ) -> Coroutine[Any, Any, T_co]:
        if not ctx.dont_replace and hasattr(ctx, original_function.__name__):
            # If dont_replace is False and the Context has an attribute with the same name as the original function,
            # replace it. No checks are performed if their signatures are equal. This must be ensured by the
            # programmer!
            replaced_f: ROut[R_out_contra, P, T_co] = getattr(
                ctx, original_function.__name__
            )
            return replaced_f(replaced_arg, *args, **kwargs)

        new_f = wrapper_function(original_function)
        return new_f(replaced_arg, *args, **kwargs)

    return ctx_callable


def ctxlize(
    original_function: Callable[P, T_co],
) -> ContextCallable[P, T_co]:
    """See `ctxlize_wrap` for full details. This is a similar function that also works on sync functions and does not
    perform any wrapping."""

    def ctx_callable(ctx: Context, *args: P.args, **kwargs: P.kwargs) -> T_co:
        if not ctx.dont_replace and hasattr(ctx, original_function.__name__):
            replaced_f: Callable[P, T_co] = getattr(ctx, original_function.__name__)
            return replaced_f(*args, **kwargs)

        return original_function(*args, **kwargs)

    return ctx_callable
