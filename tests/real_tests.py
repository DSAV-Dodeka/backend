import pytest
import asyncio

import pytest_asyncio
from httpx import AsyncClient


@pytest.fixture(scope="module")
def event_loop():
    """ Necessary for async tests with module-scoped fixtures """
    loop = asyncio.get_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="module")
async def local_client():
    async with AsyncClient(base_url="http://localhost:4243/") as local_client:
        yield local_client


@pytest.mark.asyncio
async def test_root(local_client):
    response = await local_client.get("/")

    assert response.status_code == 200
    assert response.json() == {"Hallo": "Atleten"}


@pytest.mark.asyncio
async def test_root(local_client):
    req = {
        "firstname": "mr",
        "lastname": "person",
        "email": "hi@xs.nl",
        "phone": "+31068243"
    }

    response = await local_client.post("/onboard/signup/", json=req)


