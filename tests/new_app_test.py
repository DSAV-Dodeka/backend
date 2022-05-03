import asyncio

import pytest
import pytest_asyncio
from pytest_mock import MockerFixture

from httpx import AsyncClient


@pytest.fixture(scope="module")
def event_loop():
    """ Necessary for async tests with module-scoped fixtures """
    loop = asyncio.get_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="module")
async def app_mod():
    import dodekaserver.app as app_mod

    yield app_mod


@pytest_asyncio.fixture(scope="module")
async def app(app_mod):
    # startup, shutdown is not run
    app = app_mod.create_app()
    yield app


@pytest_asyncio.fixture(scope="module", autouse=True)
async def mock_dsrc(app_mod, module_mocker: MockerFixture):
    app_mod.dsrc.gateway = module_mocker.MagicMock(spec=app_mod.dsrc.gateway)


@pytest_asyncio.fixture(scope="module")
async def test_client(app):
    async with AsyncClient(app=app, base_url="http://test") as test_client:
        yield test_client


@pytest.mark.asyncio
async def test_root(test_client):
    response = await test_client.get("/")

    assert response.status_code == 200
    assert response.json() == {"Hallo": "Atleten"}


@pytest.mark.asyncio
async def test_refresh(test_client):
    import dodekaserver.data as dta
    dsrc = dta.dsrc
    import dodekaserver.auth.tokens as tkns
    a, _ = await tkns.do_refresh(dsrc, "abc")
    assert a == ""