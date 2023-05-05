import asyncio
from pathlib import Path

import yappi
from pydantic import BaseModel
from sqlalchemy import CursorResult, text
from sqlalchemy.ext.asyncio import AsyncConnection

from apiserver import data
from apiserver.app.env import load_config
from apiserver.data import Source
from apiserver.data.db.model import USERDATA_TABLE, USER_ID, UD_ACTIVE


class UserID(BaseModel):
    user_id: str


class UserIDList(BaseModel):
    user_ids: list[UserID]


def all_rows(res: CursorResult) -> list[dict]:
    rows = list(res.mappings().all())

    new_rows = [UserID(user_id=r["user_id"]) for r in rows]

    # return [dict(rows[0])]
    return new_rows
    # return [dict(row) for row in rows]


def select_set(columns: set[str]):
    return ", ".join(columns)


async def select_some_where(
    conn: AsyncConnection,
    table: str,
    sel_col: set[str],
    where_col: str,
    where_value,
) -> list[dict]:
    """Ensure `table`, `where_col` and `sel_col` are never user-defined."""
    some = select_set(sel_col)
    query = text(f"SELECT {some} FROM {table} WHERE {where_col} = :val;")
    res = await conn.execute(query, parameters={"val": where_value})
    return all_rows(res)


async def get_all_user_ids(conn: AsyncConnection) -> list[UserID]:
    all_user_ids = await select_some_where(
        conn, USERDATA_TABLE, {USER_ID}, UD_ACTIVE, True
    )
    return all_user_ids
    # return parse_obj_as(list[UserID], all_user_ids)


async def local_dsrc():
    test_config_path = Path(__file__).parent.joinpath("localdead.toml")
    api_config = load_config(test_config_path)
    dsrc = Source()
    dsrc.init_gateway(api_config)
    await dsrc.startup(api_config)
    return dsrc


async def get_all():
    lcl_dsrc = await local_dsrc()
    a = ""
    num = 10000
    # num=100
    for i in range(num):
        async with data.get_conn(lcl_dsrc) as conn:
            a = await get_all_user_ids(conn)
            ab = [ai.dict() for ai in a]
    print(a)


def run_yappi():
    yappi.set_clock_type("WALL")
    with yappi.run():
        asyncio.run(get_all())
    yappi.get_func_stats().print_all()


run_yappi()
