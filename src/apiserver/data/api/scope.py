from typing import Any, LiteralString, Optional

from sqlalchemy.ext.asyncio import AsyncConnection

from apiserver.lib.model.entities import ScopeData, UserScopeData, RawUserScopeData
from apiserver.lib.utilities import strip_edge, usp_hex, de_usp_hex
from schema.model import (
    USER_TABLE,
    SCOPES,
    USER_ID,
    UD_FIRSTNAME,
    UD_LASTNAME,
    USERDATA_TABLE,
    UD_ACTIVE,
)
from store.db import (
    concat_column_by_unique_returning,
    select_some_where,
    update_column_by_unique,
    select_some_join_where,
)
from store.error import DataError, NoDataError, DbError


def parse_scope_data(scope_dict: Optional[dict[str, Any]]) -> ScopeData:
    if scope_dict is None:
        raise NoDataError("ScopeData does not exist.", "scope_data_empty")

    return ScopeData.model_validate(scope_dict)


def ignore_admin_member(scope: str) -> str:
    if scope in {"admin", "member"}:
        return ""
    else:
        return scope


def parse_users_scopes_data(
    users_scope_dict: Optional[dict[str, Any]]
) -> UserScopeData:
    if users_scope_dict is None:
        raise NoDataError("UserScopeData does not exist.", "user_scope_data_empty")
    raw_user_scope = RawUserScopeData.model_validate(users_scope_dict)
    name = raw_user_scope.firstname + " " + raw_user_scope.lastname
    scope_list = {
        ignore_admin_member(de_usp_hex(usph_scope))
        for usph_scope in raw_user_scope.scope.split(" ")
    }
    scope_list.discard("")
    return UserScopeData(
        name=name, user_id=raw_user_scope.user_id, scope=list(scope_list)
    )


async def add_scope(conn: AsyncConnection, user_id: str, new_scope: str) -> None:
    """Whitespace (according to Unicode standard) is removed and scope is added as usph"""
    # We strip whitespace and other nasty characters from start and end
    stripped_scope = strip_edge(new_scope)
    # Space is added because we concatenate
    # We usp_hex to make weird Unicode characters visible easily
    scope_usph = " " + usp_hex(stripped_scope)

    try:
        final_scope: str = await concat_column_by_unique_returning(
            conn, USER_TABLE, SCOPES, SCOPES, scope_usph, USER_ID, user_id, SCOPES
        )
    except DbError as e:
        raise DataError(f"{e.err_desc} from internal: {e.err_internal}", e.key)

    if final_scope is None:
        raise NoDataError(
            "No scope added, user most likely does not exist", "scope_not_added"
        )

    scope_values = final_scope.split(" ")
    if len(set(scope_values)) != len(scope_values):
        raise DataError("Scope already exists on scope", "scope_duplicate")


async def remove_scope(conn: AsyncConnection, user_id: str, old_scope: str) -> None:
    # Space is added because we concatenate
    scope_usph = usp_hex(old_scope)

    try:
        data_list = await select_some_where(
            conn, USER_TABLE, {SCOPES}, USER_ID, user_id
        )
    except DbError as e:
        raise DataError(f"{e.err_desc} from internal: {e.err_internal}", e.key)

    # With 'where USER_ID = user_id', the result should only contain one dict.
    # Maybe in the future we can make the user_id attribute a list to bulk remove roles.
    # For example a button to more easily change the board -> Remove role from old board
    if len(data_list) != 1:
        raise DataError(
            "No scope removed, user most likely does not exist", "scope_not_removed"
        )

    scope_data = parse_scope_data(dict(data_list[0]))

    scope_string = scope_data.scope
    scope_list = scope_string.split(" ")

    try:
        scope_list.remove(scope_usph)
    except ValueError:
        raise DataError("Scope does not exists on scope", "scope_nonexistent")

    result = " ".join([str(scope) for scope in scope_list])

    try:
        await update_column_by_unique(
            conn, USER_TABLE, SCOPES, result, USER_ID, user_id
        )
    except DbError as e:
        raise DataError(f"{e.err_desc} from internal: {e.err_internal}", e.key)


async def get_all_users_scopes(conn: AsyncConnection) -> list[UserScopeData]:
    # user_id must be namespaced as it exists in both tables
    select_columns: set[LiteralString] = {
        UD_FIRSTNAME,
        UD_LASTNAME,
        f"{USER_TABLE}.{USER_ID}",
        SCOPES,
    }

    all_users_scopes = await select_some_join_where(
        conn,
        select_columns,
        USER_TABLE,
        USERDATA_TABLE,
        USER_ID,
        USER_ID,
        UD_ACTIVE,
        True,
    )

    return [
        parse_users_scopes_data(dict(u_ud_scope_dct))
        for u_ud_scope_dct in all_users_scopes
    ]
