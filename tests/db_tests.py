import pytest
import asyncio

import sqlalchemy.engine
from databases import Database

import dodekaserver.db
from dodekaserver.db.settings import ADMIN_DB_NAME, DB_CLUSTER
from dodekaserver.db import model
from dodekaserver.db.admin import remove_test_dbs
from dodekaserver.utilities import random_time_hash_hex


@pytest.fixture(scope="module")
def event_loop():
    """ Necessary for async tests with module-scoped fixtures """
    loop = asyncio.get_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="module", autouse=True)
@pytest.mark.asyncio
async def test_db():
    """ Set up a database for testing, is run once each time this module is run. """

    # Random name that cannot be duplicated
    test_db_name = 'test' + random_time_hash_hex()
    admin_db_url = f"{DB_CLUSTER}/{ADMIN_DB_NAME}"
    # Connect to admin database that allows us to create new database
    database = Database(admin_db_url)
    await database.connect()

    # Remove all previous test databases
    await remove_test_dbs(database)

    query_create = f"CREATE DATABASE {test_db_name}"
    await database.execute(query_create)
    await database.disconnect()

    test_db_url = f"{DB_CLUSTER}/{test_db_name}"

    # Use the database model to create an empty database (uses SQLAlchemy connection)
    engine = sqlalchemy.engine.create_engine(test_db_url)
    with engine.begin() as connection:
        model.metadata.create_all(connection)

    # Connect to test database
    test_db = Database(test_db_url, force_rollback=True)
    await test_db.connect()

    # Send the db object to tests
    yield test_db

    # This code runs after the tests
    await test_db.disconnect()


@pytest.fixture(scope="module")
@pytest.mark.asyncio
async def test_dbops():
    yield dodekaserver.db.DatabaseOperations


@pytest.mark.asyncio
async def test_check_dbs(test_db: Database):
    query_fetch = "SELECT datname FROM pg_database"
    fetch_res = await test_db.fetch_all(query_fetch)
    # print([dict(res) for res in fetch_res])