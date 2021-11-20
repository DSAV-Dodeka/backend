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
    from dodekaserver.data import dsrc
    import dodekaserver.app as app_mod

    app = app_mod.create_app()
    await app_mod.app_startup(dsrc)
    yield app
    await app_mod.app_shutdown(dsrc)


@pytest.fixture(scope="module", autouse=True)
@pytest.mark.asyncio
async def mock(module_mocker: MockerFixture):
    # dsrc_mock = module_mocker.patch('dodekaserver.data.dsrc', None)
    pass
    # retrieve_mock = module_mocker.patch('dodekaserver.db.use.retrieve_by_id')
    #
    # def side_effect(a, b, c):
    #     return {'id': 126, 'name': 'YOURNAME', 'last_name': 'YOURLASTNAME'}
    #
    # retrieve_mock.side_effect = side_effect


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


@pytest.mark.asyncio
async def test_user(test_client):
    response = await test_client.get("/users/126")

    assert response.status_code == 200
    assert response.json() == {'user': "{'id': 126, 'name': 'YOURNAME', 'last_name': 'YOURLASTNAME'}"}

# @pytest.fixture(scope="module")
# def test_client():
#     from dodekaserver.app import app
#     with TestClient(app) as test_client:
#         yield test_client
#
#
# def test_root(test_client):
#     response = test_client.get("")
#
#     assert response.status_code == 200
#     assert response.json() == {"Hallo": "Atleten"}
#     print(response)
