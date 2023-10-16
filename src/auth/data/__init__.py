# Currently, we rely on the import of these modules for all contexts to be run at startup

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
