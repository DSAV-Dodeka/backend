import os
from random import randint

import pytest
import pytest_asyncio
from sqlalchemy import text
from apiserver.data.source import Source


from apiserver.env import Config, load_config
from test_util import Fixture, AsyncFixture
from store.conn import get_conn
from store.db import insert
from store.store import Store
from test_resources import res_path


if not os.environ.get("QUERY_TEST"):
    pytest.skip(
        "Skipping store_test as QUERY_TEST is not set.", allow_module_level=True
    )


def test_something():
    assert True is True


@pytest.fixture(scope="module")
def api_config() -> Fixture[Config]:
    test_config_path = res_path.joinpath("querytestenv.toml")
    yield load_config(test_config_path)


@pytest_asyncio.fixture(scope="module")
async def local_store(api_config):
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


async def test_insert(local_store: Store, setup_table: str):
    async with get_conn(local_store) as conn:
        pass
