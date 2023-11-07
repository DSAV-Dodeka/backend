from auth.data import authorize
from auth.data import authentication
from auth.data import register
from auth.data import token
from auth.data import keys
from auth.data import update

__all__ = [
    "authorize",
    "authentication",
    "register",
    "token",
    "keys",
    "update",
]

"""
The `auth` module assumes the following are available:

- A database with unknown schema
- A key-value store for persisting data temporarily, with support for JSON

It relies on the `store` module for interacting with them. The `store` module assumes that you use PostgreSQL and
Redis, but these dependencies are easily swapped out.

As key-value store operations do not rely on a schema, we directly use the `store` functions to load and store JSON
and plain strings. Providing an interface is an unnecessary abstraction in our case, but could still be done quite
easily.

However, even though it doesn't rely on a specific schema, some of its operations do rely on the existence of some
basic relations. These operations, and the requirements on the relations, are found the in the `relational` module.

The relations necessary for storing information for OPAQUE are assumed to not interfer with any existing schema.
Therefore, they are directly implemented using `store` operations. However, the only required function,
`get_apake_setup`, is implemented in a Context, meaning it can be overriden by the consuming application.

TODO dep inj for opaque setup table name

Three other relations are assumed to exist:
- User identity/scope
- User data
- Refresh tokens

The user identity and allowed scope relation must include at least the following:
- user_id: str
- email: str
- password_file: str
- scope: str

Some application-specific decision on when e-mail is necessary have been made, but these should not be too hard to swap
out.

User data can include any information that is necessary for building the additional info required by the consuming
application in the ID token.

Finally, refresh tokens make more strict assumptions about how they look like. As they are not as simple as the OPAQUE
setup, no implementation is provided. This must be done by the consuming application.
"""
