import asyncio
import random

import pytest
import pytest_asyncio
from pytest_mock import MockerFixture

from httpx import AsyncClient

from dodekaserver.auth.models import FlowUser, AuthRequest
from dodekaserver.data import Source
from dodekaserver.db import DatabaseOperations
from dodekaserver.env import frontend_client_id
import dodekaserver.data.key
from dodekaserver.utilities import utc_timestamp
from dodekaserver.db.model import KEY_TABLE, REFRESH_TOKEN_TABLE


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
    dsrc_mock = module_mocker.patch('dodekaserver.data.dsrc', spec=Source)
    yield dsrc_mock


@pytest_asyncio.fixture(scope="module")
async def mock_dbop(module_mocker: MockerFixture, mock_dsrc):
    dbop_mock = module_mocker.patch('dodekaserver.db.use.DatabaseOperations', spec=DatabaseOperations)
    mock_dsrc.ops = dbop_mock
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


# @pytest.mark.asyncio
# async def test_start_login(module_mocker: MockerFixture, test_client):
#     # ('4shu3p963tb5GATtor7QE-5txnuKB2sr9ypVASvFGAc', 'anBhXnlJ3r212O-6vfeEm8hQQlmr_RXlb9fD0I_3xX8')
#     # password file abcde:abcde
#     # HzNNbWK5Ms5cEsYZ0BERY6oiDaMVfpuYs844SH3o4QH4-4GCqCmoVRomoIGjNwHW_o6eDkx6c91cUtljoB9JZAFLTkJXK8YQqjUAyxyk8eyJhLLsiJCH2JvkPDPY1VcOzMqBBzgZOyndW7tomyUIHaVUqV9PY-Lnv8KEl6Q7_eHYeSzKK6cy1nDBjeWZ0IyullsqxNzUwDZMNcW9oRU8dXBOnN7EbzPaHqyLTNU4u8GfU2heKf5L35C9uKtCWPsItg
#     gt_key = module_mocker.patch('dodekaserver.data.key.get_opaque_private')
#     gt_key.return_value = "4shu3p963tb5GATtor7QE-5txnuKB2sr9ypVASvFGAc"
#     get_pass = module_mocker.patch('dodekaserver.data.user.get_user_by_usph')
#     get_pass.password_file = "HzNNbWK5Ms5cEsYZ0BERY6oiDaMVfpuYs844SH3o4QH4-4GCqCmoVRomoIGjNwHW_o6eDkx6c91cUtljoB9JZA" \
#                              "FLTkJXK8YQqjUAyxyk8eyJhLLsiJCH2JvkPDPY1VcOzMqBBzgZOyndW7tomyUIHaVUqV9PY-Lnv8KEl6Q7_eHY" \
#                              "eSzKK6cy1nDBjeWZ0IyullsqxNzUwDZMNcW9oRU8dXBOnN7EbzPaHqyLTNU4u8GfU2heKf5L35C9uKtCWPsItg"


@pytest.mark.asyncio
async def test_incorrect_client_id(module_mocker: MockerFixture, test_client: AsyncClient):
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
async def test_incorrect_grant_type(module_mocker: MockerFixture, test_client: AsyncClient):
    req = {
      "client_id": frontend_client_id,
      "grant_type": "wrong",
      "code": "",
      "redirect_uri": "",
      "code_verifier": "",
      "refresh_token": ""
    }

    response = await test_client.post("/oauth/token/", json=req)
    assert response.status_code == 400
    res_j = response.json()
    assert res_j["error"] == "unsupported_grant_type"


@pytest.mark.asyncio
async def test_empty_verifier(module_mocker: MockerFixture, test_client: AsyncClient):
    req = {
        "client_id": frontend_client_id,
        "grant_type": "authorization_code",
        "code": "some",
        "redirect_uri": "some",
        "code_verifier": "",
        "refresh_token": ""
    }

    response = await test_client.post("/oauth/token/", json=req)
    assert response.status_code == 400
    res_j = response.json()
    assert res_j["error"] == "invalid_request"
    assert res_j["debug_key"] == "incomplete_code"


@pytest.mark.asyncio
async def test_missing_redirect(module_mocker: MockerFixture, test_client: AsyncClient):
    req = {
        "client_id": frontend_client_id,
        "grant_type": "authorization_code",
        "code": "some",
        "code_verifier": "some",
        "refresh_token": ""
    }

    response = await test_client.post("/oauth/token/", json=req)
    assert response.status_code == 400
    res_j = response.json()
    assert res_j["error"] == "invalid_request"
    assert res_j["debug_key"] == "incomplete_code"


@pytest.mark.asyncio
async def test_empty_code(module_mocker: MockerFixture, test_client: AsyncClient):
    req = {
        "client_id": frontend_client_id,
        "grant_type": "authorization_code",
        "code": "",
        "redirect_uri": "some",
        "code_verifier": "some",
        "refresh_token": ""
    }

    response = await test_client.post("/oauth/token/", json=req)
    assert response.status_code == 400
    res_j = response.json()
    assert res_j["error"] == "invalid_request"
    assert res_j["debug_key"] == "incomplete_code"


session_key = "somecomplexsessionkey"
mock_redirect = "http://localhost:3000/auth/callback"


@pytest_asyncio.fixture
async def mock_kv(module_mocker: MockerFixture, mock_dsrc):
    get_json = module_mocker.patch('dodekaserver.data.get_json')
    mock_flow_id = "1d5c621ea3a2da319fe0d0a680046fd6369a60e450ff04f59c51b0bfb3d96eef"
    mock_flow_user = FlowUser(user_usph="mrmock", auth_time=utc_timestamp()-20, flow_id=mock_flow_id).dict()
    mock_auth_request = AuthRequest(response_type="code", client_id="dodekaweb_client",
                                    redirect_uri=mock_redirect,
                                    state="KV6A2hTOv6mOFYVpTAOmWw",
                                    code_challenge="OFohb0gwrsAV6Zsvlvr3upWjO1JAiUa9bxtrOrVYELg",
                                    code_challenge_method="S256",
                                    nonce="-eB2lpr1IqZdJzt9CfDZ5jrHGa6yE87UUTFd4CWweOI").dict()
    nonce_original = "6SWk9T1sUfqgSYeq2XlawA"

    def side_effect(kv, key):
        if kv == mock_dsrc.kv:
            if key == session_key:
                return mock_flow_user
            elif key == mock_flow_id:
                return mock_auth_request
            else:
                return None
        else:
            raise ValueError

    get_json.side_effect = side_effect


@pytest_asyncio.fixture
async def mock_retrieve_id_key(mock_dbop, mock_dsrc):
    mock_opq_key = {
        'id': 0, 'algorithm': 'curve25519ristretto', 'public': 'lB8G80Go8xwpSGEWuayAfAGirKr70DSUfFCpX20aWx4',
        'private': 'WCvFeJjVeYhXWrg1YKflgqsgzB_fmhXcL0BFcCtTVQY', 'public_format': 'none',
        'public_encoding': 'base64url', 'private_format': 'none', 'private_encoding': 'base64url'
    }
    mock_symm_key = {
        'id': 2, 'algorithm': 'symmetric', 'public': None, 'private': '8T3oEm_haJZbn6xu-klttJXk5QBPYlurQrqA5SDx-Ck',
        'public_format': None, 'public_encoding': None, 'private_format': 'none', 'private_encoding': 'base64url'
    }
    mock_token_key = {
        'id': 1, 'algorithm': 'ed448',
        'public': '-----BEGIN PUBLIC KEY-----\nMEMwBQYDK2VxAzoAtPGddEupA3b5P5yr9gT3rvjzWeQH5cedY6RcwN3A5zTS9n8C\nc6dOR+'
                  'XUPVLVu0o0i/t46fW1HMQA\n-----END PUBLIC KEY-----\n',
        'private': '-----BEGIN PRIVATE KEY-----\nMEcCAQAwBQYDK2VxBDsEOY1wa98ZvsK8pYML+ICD9Mbtavr+QC5PC301oVn5jPM6\nT8tE'
                   'CKaZvu5mxG/OfxlEKxl/XIKuClP1mw==\n-----END PRIVATE KEY-----\n',
        'public_format': 'X509PKCS#1', 'public_encoding': 'PEM', 'private_format': 'PKCS#8', 'private_encoding': 'PEM'
    }

    mock_keys = {
        0: mock_opq_key,
        1: mock_token_key,
        2: mock_symm_key
    }

    async def retrieve_by_id_mock(db, table, id_int):
        if db == mock_dsrc.db:
            if table == KEY_TABLE:
                return mock_keys.get(id_int)

    mock_dbop.retrieve_by_id.side_effect = retrieve_by_id_mock
    yield mock_dbop


@pytest_asyncio.fixture
async def mock_insert_return_id_refresh(mock_dbop, mock_dsrc):
    async def insert_return_id_mock(db, table, row):
        if db == mock_dsrc.db:
            if table == REFRESH_TOKEN_TABLE:
                return 74

    mock_dbop.insert_return_id.side_effect = insert_return_id_mock
    yield mock_dbop


@pytest.mark.asyncio
async def test_wrong_code(mock_kv, test_client: AsyncClient):
    req = {
        "client_id": frontend_client_id,
        "grant_type": "authorization_code",
        "code": "wrong",
        "redirect_uri": "some",
        "code_verifier": "some",
        "refresh_token": ""
    }

    response = await test_client.post("/oauth/token/", json=req)
    assert response.status_code == 400
    res_j = response.json()
    assert res_j["error"] == "invalid_grant"
    assert res_j["debug_key"] == "empty_flow"


@pytest.mark.asyncio
async def test_code(mock_kv, mock_retrieve_id_key, mock_insert_return_id_refresh, test_client: AsyncClient):
    verifier = "aIhn-rcznAqlfjvmaX7aS3ZLcmycIGWWnnAFDEn-VLI"
    req = {
        "client_id": frontend_client_id,
        "grant_type": "authorization_code",
        "code": session_key,
        "redirect_uri": mock_redirect,
        "code_verifier": verifier
    }

    response = await test_client.post("/oauth/token/", json=req)
    assert response.status_code == 200
    res_j = response.json()
    print(res_j)
    # {'id_token': 'eyJ0eXAiOiJKV1QiLCJhbGciOiJFZERTQSJ9.eyJzdWIiOiJtcm1vY2siLCJpc3MiOiJodHRwczovL2RzYXZkb2Rla2EubmwvYXV0aCIsImF1ZCI6WyJkb2Rla2F3ZWJfY2xpZW50Il0sImF1dGhfdGltZSI6MTY0ODM4MjI5Miwibm9uY2UiOiItZUIybHByMUlxWmRKenQ5Q2ZEWjVqckhHYTZ5RTg3VVVURmQ0Q1d3ZU9JIiwiaWF0IjoxNjQ4MzgyMzEyLCJleHAiOjE2NDg0MTgzMTJ9.yI1SySLtDPgcbGktsJhh5kW2dt97Z2o__DBXrhYfFb68MlMFXa38BnTBTE8Kqe7nnXVF1SkzTacA3MfgFufND4HT0S56R-hI9Tq091tevazxPYfYGF-Se5IzqOer66TTnjpTl5bUFGqYQP0OaS6WaTIA', 'access_token': 'eyJ0eXAiOiJKV1QiLCJhbGciOiJFZERTQSJ9.eyJzdWIiOiJtcm1vY2siLCJpc3MiOiJodHRwczovL2RzYXZkb2Rla2EubmwvYXV0aCIsImF1ZCI6WyJkb2Rla2F3ZWJfY2xpZW50IiwiZG9kZWthYmFja2VuZF9jbGllbnQiXSwic2NvcGUiOiJ0ZXN0IiwiaWF0IjoxNjQ4MzgyMzEyLCJleHAiOjE2NDgzODU5MTJ9.h6WOdEv5XmDKlloC-e_Mdd4P9MxTnaL16UeiL4lpARQsUyR6VRuapljFvjNaPH2BKxsqlAuLJVwAVCY03XQllz0l555pRPs01AsjBFJlGhBBwqAfuF9ionUPMbxbwsgh-W30t5QJk76tgfzGLF4TETcA', 'refresh_token': 'Pne6w5l14knJ12cP_djtxXi9zHrEXxaWYIoJqwcX6I2Vz7UdiieWIyAqcE-7LYSshU9YKKCGqJFBFTr3hAykrvT1c_1p4teQV9qibPwe5XY36H369tG2uXo', 'token_type': 'Bearer', 'expires_in': 3600, 'scope': 'test'}


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
