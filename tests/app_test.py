import asyncio

import pytest
from pytest_mock import MockerFixture

from httpx import AsyncClient


@pytest.fixture(scope="module")
def event_loop():
    """ Necessary for async tests with module-scoped fixtures """
    loop = asyncio.get_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="module")
@pytest.mark.asyncio
async def app():
    import dodekaserver.app as app_mod
    # startup, shutdown is not run
    app = app_mod.create_app()
    yield app


@pytest.fixture(scope="module", autouse=True)
@pytest.mark.asyncio
async def mock_dbop(module_mocker: MockerFixture):
    dsrc_mock = module_mocker.patch('dodekaserver.data.dsrc', autospec=True)
    dbop_mock = module_mocker.patch('dodekaserver.db.use.DatabaseOperations', autospec=True)
    dsrc_mock.ops = dbop_mock
    yield dbop_mock


@pytest.fixture(scope="module")
@pytest.mark.asyncio
async def test_client(app):
    async with AsyncClient(app=app, base_url="http://test") as test_client:
        yield test_client


@pytest.mark.asyncio
async def test_root(test_client):
    response = await test_client.get("/")

    assert response.status_code == 200
    assert response.json() == {"Hallo": "Atleten"}


@pytest.fixture
async def mock_user_retrieve(mock_dbop):
    user_row = {'id': 0, 'name': 'TEST', 'last_name': 'TEST_LAST'}

    async def mock_retrieve(a, b, row_id):
        user_row['id'] = row_id
        return user_row

    mock_dbop.retrieve_by_id = mock_retrieve

    yield user_row


@pytest.mark.asyncio
async def test_get_user(mock_user_retrieve, test_client):

    response = await test_client.get("/users/126")

    assert response.status_code == 200

    assert response.json() == {"user": mock_user_retrieve}
