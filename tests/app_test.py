import asyncio

import pytest
import pytest_asyncio
from pytest_mock import MockerFixture

from httpx import AsyncClient

from dodekaserver.env import frontend_client_id
import dodekaserver.data.key


@pytest.fixture(scope="module")
def event_loop():
    """ Necessary for async tests with module-scoped fixtures """
    loop = asyncio.get_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="module")
async def app():
    import dodekaserver.app as app_mod
    # startup, shutdown is not run
    app = app_mod.create_app()
    yield app


@pytest_asyncio.fixture(scope="module", autouse=True)
async def mock_dsrc(module_mocker: MockerFixture):
    dsrc_mock = module_mocker.patch('dodekaserver.data.dsrc', autospec=True)
    yield dsrc_mock


@pytest_asyncio.fixture(scope="module")
async def mock_dbop(module_mocker: MockerFixture):
    dsrc_mock = module_mocker.patch('dodekaserver.data.dsrc', autospec=True)
    dbop_mock = module_mocker.patch('dodekaserver.db.use.DatabaseOperations', autospec=True)
    dsrc_mock.ops = dbop_mock
    yield dbop_mock


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
async def test_start_login(module_mocker: MockerFixture, test_client):
    # ('4shu3p963tb5GATtor7QE-5txnuKB2sr9ypVASvFGAc', 'anBhXnlJ3r212O-6vfeEm8hQQlmr_RXlb9fD0I_3xX8')
    # password file abcde:abcde
    # HzNNbWK5Ms5cEsYZ0BERY6oiDaMVfpuYs844SH3o4QH4-4GCqCmoVRomoIGjNwHW_o6eDkx6c91cUtljoB9JZAFLTkJXK8YQqjUAyxyk8eyJhLLsiJCH2JvkPDPY1VcOzMqBBzgZOyndW7tomyUIHaVUqV9PY-Lnv8KEl6Q7_eHYeSzKK6cy1nDBjeWZ0IyullsqxNzUwDZMNcW9oRU8dXBOnN7EbzPaHqyLTNU4u8GfU2heKf5L35C9uKtCWPsItg
    gt_key = module_mocker.patch('dodekaserver.data.key.get_opaque_private')
    gt_key.return_value = "4shu3p963tb5GATtor7QE-5txnuKB2sr9ypVASvFGAc"
    get_pass = module_mocker.patch('dodekaserver.data.user.get_user_by_usph')
    get_pass.password_file = "HzNNbWK5Ms5cEsYZ0BERY6oiDaMVfpuYs844SH3o4QH4-4GCqCmoVRomoIGjNwHW_o6eDkx6c91cUtljoB9JZA" \
                             "FLTkJXK8YQqjUAyxyk8eyJhLLsiJCH2JvkPDPY1VcOzMqBBzgZOyndW7tomyUIHaVUqV9PY-Lnv8KEl6Q7_eHY" \
                             "eSzKK6cy1nDBjeWZ0IyullsqxNzUwDZMNcW9oRU8dXBOnN7EbzPaHqyLTNU4u8GfU2heKf5L35C9uKtCWPsItg"


@pytest.mark.asyncio
async def test_token_refresh(module_mocker: MockerFixture, test_client: AsyncClient):
    req = {
      "client_id": "incorrect",
      "grant_type": "",
      "code": "",
      "redirect_uri": "",
      "code_verifier": "",
      "refresh_token": ""
    }
    response = await test_client.post("/oauth/token/", json=req)
    assert response.status_code == 400
    assert response.json()["error"] == "invalid_client"
    # print(response.request.content)
    # print(response.text)
    # print(response.json())
    # print(response)


@pytest.mark.asyncio
async def test_token_refresh(module_mocker: MockerFixture, test_client: AsyncClient):
    req = {
      "client_id": frontend_client_id,
      "grant_type": "",
      "code": "",
      "redirect_uri": "",
      "code_verifier": "",
      "refresh_token": ""
    }

    response = await test_client.post("/oauth/token/", json=req)
    assert response.status_code == 400
    res_j = response.json()
    assert res_j["error"] == "invalid_request"
    assert res_j["error_description"] == "Only 'refresh_token' and 'authorization_code' grant types are available."

# @pytest.fixture
# async def mock_user_retrieve(mock_dbop):
#     user_row = {'id': 0, 'name': 'TEST', 'last_name': 'TEST_LAST'}
#
#     async def mock_retrieve(a, b, row_id):
#         user_row['id'] = row_id
#         return user_row
#
#     mock_dbop.retrieve_by_id = mock_retrieve
#
#     yield user_row
#
#
# @pytest.mark.asyncio
# async def test_get_user(mock_user_retrieve, test_client):
#
#     response = await test_client.get("/users/126")
#
#     assert response.status_code == 200
#
#     assert response.json() == {"user": mock_user_retrieve}
