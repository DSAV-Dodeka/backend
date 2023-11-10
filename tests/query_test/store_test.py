import asyncio
import os
from random import randint
from typing import LiteralString

import pytest
import pytest_asyncio
from sqlalchemy import text
from apiserver.app.ops.startup import drop_create_database


from apiserver.env import Config, load_config
from tests.test_util import Fixture, AsyncFixture
from store.conn import get_conn
from store.store import Store
from store.db import LiteralDict, insert
from tests.test_resources import res_path


if not os.environ.get("QUERY_TEST"):
    pytest.skip(
        "Skipping store_test as QUERY_TEST is not set.", allow_module_level=True
    )


@pytest.fixture(scope="session", autouse=True)
def event_loop():
    """Necessary for async tests with module-scoped fixtures"""
    loop = asyncio.get_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="module")
def api_config() -> Fixture[Config]:
    test_config_path = res_path.joinpath("querytestenv.toml")
    yield load_config(test_config_path)


@pytest_asyncio.fixture(scope="module")
async def local_store(api_config: Config):
    # each module makes its own database
    api_config.DB_NAME = f"testdb_{randint(0, 100000)}"
    drop_create_database(api_config)
    store = Store()
    store.init_objects(api_config)
    await store.startup()
    yield store


@pytest_asyncio.fixture
async def setup_table(local_store: Store) -> AsyncFixture[str]:
    table_name = f"table_{randint(0, 100000)}"
    async with get_conn(local_store) as conn:
        query = text(f"""
        CREATE TABLE {table_name} (
            first integer,
            second text,
            third text
        );
        """)

        await conn.execute(query)

    yield table_name

    async with get_conn(local_store) as conn:
        query = text(f"""
        DROP TABLE {table_name};
        """)

        await conn.execute(query)


@pytest.mark.asyncio
async def test_insert(local_store: Store, setup_table: LiteralString):
    row: LiteralDict = {"first": 3, "second": "some", "third": "other"}
    async with get_conn(local_store) as conn:
        cnt = await insert(conn, setup_table, row)
        assert cnt == 1

        query = text(f"""
        SELECT * FROM {setup_table};
        """)

        res = await conn.execute(query)

        res_item = res.mappings().first()

    assert res_item is not None
    assert dict(res_item) == row
