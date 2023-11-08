import asyncio
from datetime import date
import os
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy import Engine, create_engine, text
from apiserver.data.api.classifications import insert_classification


from apiserver.env import Config, load_config
from schema.model.model import (
    CLASS_END_DATE,
    CLASS_HIDDEN_DATE,
    CLASS_START_DATE,
    CLASS_TYPE,
    CLASSIFICATION_TABLE,
)
from test_util import Fixture
from store.conn import get_conn
from store.store import Store
from test_resources import res_path

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


@pytest.fixture(scope="module")
def admin_engine(api_config) -> Fixture[Engine]:
    db_cluster = f"{api_config.DB_USER}:{api_config.DB_PASS}@{api_config.DB_HOST}:{api_config.DB_PORT}"
    admin_db_url = f"{db_cluster}/{api_config.DB_NAME_ADMIN}"

    admin_engine = create_engine(
        f"postgresql+psycopg://{admin_db_url}", isolation_level="AUTOCOMMIT"
    )

    yield admin_engine


@pytest_asyncio.fixture
async def new_db_store(api_config: Config, admin_engine: Engine):
    db_name = f"db_{uuid4()}"

    with admin_engine.connect() as conn:
        create_db = text(f"CREATE DATABASE {db_name}")
        conn.execute(create_db)

    modified_config = api_config.model_copy(update={"DB_NAME": db_name})

    store = Store()
    store.init_objects(modified_config)
    # we don't run startup due to its overhead
    yield store
    # Ensure connections are GC'd
    del store

    with admin_engine.connect() as conn:
        drop_db = text(f"DROP DATABASE {db_name}")
        conn.execute(drop_db)


async def test_create_class(new_db_store: Store):
    async with get_conn(new_db_store) as conn:
        await insert_classification(conn, "points", date(2022, 1, 1))

        query = text(f"""
        SELECT * FROM {CLASSIFICATION_TABLE};
        """)

        res = await conn.execute(query)

        res_item = res.mappings().first()

    assert res_item is not None
    assert res_item[CLASS_TYPE] == "points"
    assert res_item[CLASS_START_DATE] == date(2022, 1, 1)
    assert res_item[CLASS_END_DATE] == date(2022, 5, 31)
    assert res_item[CLASS_HIDDEN_DATE] == date(2022, 5, 1)
