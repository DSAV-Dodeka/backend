import asyncio

import multiprocessing as mp

import pytest
from pytest_mock import MockerFixture

import httpx

import dodekaserver.data

import uvicorn

import time


@pytest.fixture(scope="module")
def event_loop():
    """ Necessary for async tests with module-scoped fixtures """
    loop = asyncio.get_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="module", autouse=True)
def mock_dsrc(module_mocker: MockerFixture):
    m_dsrc = module_mocker.patch('dodekaserver.data.Source', spec=dodekaserver.data.Source)
    m_dsrc.db = None


@pytest.fixture(scope="module")
@pytest.mark.asyncio
async def test_client():
    uvi_kwargs = {"host": "127.0.0.1", "port": 4242}
    uvi_process = mp.Process(target=uvicorn.run, args=("dodekaserver.app:app",), kwargs=uvi_kwargs)
    uvi_process.start()

    time.sleep(0.5)
    client = httpx.AsyncClient()
    yield client
    await client.aclose()

    uvi_process.kill()


@pytest.mark.asyncio
async def test_root(test_client):
    response = await test_client.get("http://localhost:4242/")

    assert response.status_code == 200
    assert response.json() == {"Hallo": "Atleten"}
    print(response)


@pytest.mark.asyncio
async def test_get_user(test_client):
    user_id = 126

    # retrieve_mock = mocker.patch('dodekaserver.db')
    # retrieve_mock.retrieve_by_id = None
    #
    # def side_effect(a, b, c):
    #     return {'id': 126, 'name': 'YOURNAME', 'last_name': 'YOURLASTNAME'}
    #
    # retrieve_mock.side_effect = side_effect

    response = await test_client.get(f"http://localhost:4242/users/{user_id}")
    print(response.json())

    # retrieve_by_id('a', 'b', 'c')

    # retrieve_mock.assert_called()

    assert response.status_code == 200
    assert response.json() == {
        "Hello": "{'id': 126, 'name': 'YOURNAME', 'last_name': 'YOURLASTNAME'}"
    }
