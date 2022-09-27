from pathlib import Path
import asyncio

import pytest
import pytest_asyncio

from httpx import AsyncClient

from apiserver.resources import project_path
from apiserver.env import load_config
import apiserver.utilities as util
from apiserver.auth.tokens import create_tokens, finish_tokens
from apiserver.data import Source
from apiserver.auth.tokens_data import get_keys


@pytest.fixture(scope="module")
def event_loop():
    """ Necessary for async tests with module-scoped fixtures """
    loop = asyncio.get_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="module")
def api_config():
    test_config_path = project_path.joinpath("localenv.toml")
    yield load_config(test_config_path)


@pytest_asyncio.fixture(scope="module")
async def local_client():
    async with AsyncClient(base_url="http://localhost:4243/") as local_client:
        yield local_client


@pytest.mark.asyncio
async def test_onboard_signup(local_client: AsyncClient):
    req = {
        "firstname": "mr",
        "lastname": "person",
        "email": "comcom@dsavdodeka.nl",
        "phone": "+31068243"
    }
    response = await local_client.post("/onboard/signup/", json=req)
    print(response.json())