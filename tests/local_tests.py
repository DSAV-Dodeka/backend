from pathlib import Path
import asyncio

import pytest
import pytest_asyncio

from httpx import AsyncClient
import opaquepy as opq

from apiserver.define.entities import SignedUp
from apiserver.resources import project_path
from apiserver.env import load_config
import apiserver.utilities as util
from apiserver.auth.tokens import create_tokens, finish_tokens
import apiserver.data as data
from apiserver.data import Source
from apiserver.auth.tokens_data import get_keys


@pytest.fixture(scope="module", autouse=True)
def event_loop():
    """ Necessary for async tests with module-scoped fixtures """
    loop = asyncio.get_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="module")
def api_config():
    test_config_path = Path(__file__).parent.joinpath("localdead.toml")
    yield load_config(test_config_path)


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
async def test_onboard_signup(local_client):
    req = {
        "firstname": "mr",
        "lastname": "person",
        "email": "hi@xs.nl",
        "phone": "+31068243"
    }

    response = await local_client.post("/onboard/signup/", json=req)
    print(response.json())


@pytest_asyncio.fixture(scope="module")
async def local_dsrc(api_config):
    dsrc = Source()
    dsrc.init_gateway(api_config)
    await dsrc.startup()
    yield dsrc


@pytest_asyncio.fixture(scope="module")
async def admin_access(local_dsrc):
    admin_id = "admin_test"
    scope = "member admin"
    utc_now = util.utc_timestamp()

    access_token_data, id_token_data, access_scope, refresh_save = create_tokens(admin_id, scope, utc_now, "test_nonce",
                                                                                 utc_now)
    refresh_id = 5252626
    aesgcm, signing_key = await get_keys(local_dsrc)
    refresh_token, access_token, id_token = finish_tokens(refresh_id, refresh_save, aesgcm, access_token_data,
                                                          id_token_data, utc_now, signing_key, nonce="")
    yield access_token


@pytest.mark.asyncio
async def test_generate_admin(local_dsrc: Source):
    admin_password = "admin"
    async with data.get_conn(local_dsrc) as conn:
        setup = await data.opaquesetup.get_setup(local_dsrc, conn)

    cl_req, cl_state = opq.register_client(admin_password)
    serv_resp = opq.register(setup, cl_req, util.usp_hex('1_fakerecord'))
    cl_fin = opq.register_client_finish(cl_state, admin_password, serv_resp)
    pw_file = opq.register_finish(cl_fin)

    print(pw_file)


@pytest.mark.asyncio
async def test_fill_signedup(local_dsrc):
    for i in range(5):
        signed_up = SignedUp(firstname="abc", lastname="abclast", email=f"abc{i}@abc.nl", phone="06")
        await data.signedup.insert_su_row(local_dsrc, signed_up.dict())



@pytest.mark.asyncio
async def test_onboard_confirm(local_client: AsyncClient, admin_access):
    req = {
        "email": "comcom@dsavdodeka.nl",
        "av40id": "+31068243",
        "joined": "2022-04-03"
    }
    headers = {'Authorization': f'Bearer {admin_access}'}
    response = await local_client.post("/onboard/confirm/", json=req, headers=headers)
    print(response.json())

