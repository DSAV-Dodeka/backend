from apiserver.data.context.app_context import (
    SourceContexts,
    Code,
    RegisterAppContext,
    UpdateContext,
    RankingContext,
)

__all__ = [
    "SourceContexts",
    "RegisterAppContext",
    "UpdateContext",
    "RankingContext",
    "Code",
]

"""Context functions are the core of the application, as they should contain the majority of the stateful, impure code
as they interact directly with the various database procedures. They can be called directly by router functions or by
`modules` functions. They should be the ones that open connections. These functions should have as little business logic
as possible, that should be handled by `lib` functions. You should not worry too much about testing these functions, as
this can be challenging due to the many database calls. Instead, test the underlying data functions using query tests
and the business logic in unit tests.

Small business logic can be separated into functions inside the file. If it is also used by the router or other files,
then move it into `lib`."""
