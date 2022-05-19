import asyncio

import pytest
import pytest_asyncio
from pytest_mock import MockerFixture

from httpx import AsyncClient

from dodekaserver.define import FlowUser, AuthRequest
from dodekaserver.env import frontend_client_id
from dodekaserver.utilities import utc_timestamp
from dodekaserver.define.entities import SavedRefreshToken
from dodekaserver.db.ops import DbOperations


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
    app = app_mod.app
    yield app


@pytest_asyncio.fixture(scope="module", autouse=True)
async def mock_dsrc(app_mod, module_mocker: MockerFixture):
    app_mod.dsrc.gateway = module_mocker.MagicMock(spec=app_mod.dsrc.gateway)
    app_mod.dsrc.gateway.ops = module_mocker.MagicMock(spec=DbOperations)
    yield app_mod.dsrc


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
async def test_incorrect_client_id(test_client: AsyncClient):
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


@pytest.mark.asyncio
async def test_incorrect_grant_type(test_client: AsyncClient):
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
async def test_empty_verifier(test_client: AsyncClient):
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
async def test_missing_redirect(test_client: AsyncClient):
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
async def test_empty_code(test_client: AsyncClient):
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


@pytest_asyncio.fixture
async def mock_get_keys(module_mocker: MockerFixture):
    get_k_s = module_mocker.patch('dodekaserver.data.key.get_refresh_symmetric')
    get_k_s.return_value = mock_symm_key['private']
    get_k_p = module_mocker.patch('dodekaserver.data.key.get_token_private')
    get_k_p.return_value = mock_token_key['private']


session_key = "somecomplexsessionkey"
mock_redirect = "http://localhost:3000/auth/callback"
mock_flow_id = "1d5c621ea3a2da319fe0d0a680046fd6369a60e450ff04f59c51b0bfb3d96eef"
mock_flow_user = FlowUser(user_usph="mrmock", auth_time=utc_timestamp()-20, flow_id=mock_flow_id)
mock_auth_request = AuthRequest(response_type="code", client_id="dodekaweb_client",
                                redirect_uri=mock_redirect,
                                state="KV6A2hTOv6mOFYVpTAOmWw",
                                code_challenge="OFohb0gwrsAV6Zsvlvr3upWjO1JAiUa9bxtrOrVYELg",
                                code_challenge_method="S256",
                                nonce="-eB2lpr1IqZdJzt9CfDZ5jrHGa6yE87UUTFd4CWweOI")
nonce_original = "6SWk9T1sUfqgSYeq2XlawA"
fake_token_scope = "test"
fake_token_id = 44


@pytest_asyncio.fixture
async def fake_tokens():
    from dodekaserver.auth.tokens import create_tokens, aes_from_symmetric, finish_tokens, encode_token_dict
    utc_now = utc_timestamp()
    access_token_data, id_token_data, access_scope, refresh_save = \
        create_tokens(mock_flow_user.user_usph, fake_token_scope, mock_flow_user.auth_time, mock_auth_request.nonce, utc_now)

    acc_val = encode_token_dict(access_token_data.dict())
    id_val = encode_token_dict(id_token_data.dict())

    aesgcm = aes_from_symmetric(mock_symm_key['private'])
    signing_key = mock_token_key['private']

    refresh_token, access_token, id_token = finish_tokens(fake_token_id, refresh_save, aesgcm, access_token_data,
                                                          id_token_data, utc_now, signing_key, nonce="")
    yield {'refresh': refresh_token, 'access': access_token, 'id': id_token, 'family_id': refresh_save.family_id,
           'iat': refresh_save.iat, 'exp': refresh_save.exp, 'nonce': refresh_save.nonce, 'acc_val': acc_val,
           'id_val': id_val}


@pytest.mark.asyncio
async def test_refresh(test_client, module_mocker: MockerFixture, mock_get_keys, fake_tokens):

    get_r = module_mocker.patch('dodekaserver.data.refreshtoken.get_refresh_by_id')
    get_refr = module_mocker.patch('dodekaserver.data.refreshtoken.refresh_transaction')

    def side_effect(dsrc, id_int):
        if id_int == fake_token_id:
            return SavedRefreshToken(family_id=fake_tokens['family_id'], access_value=fake_tokens['acc_val'],
                                     id_token_value=fake_tokens['id_val'], iat=fake_tokens['iat'], exp=fake_tokens['exp'],
                                     nonce=fake_tokens['nonce'])
    get_r.side_effect = side_effect
    get_refr.return_value = 45

    req = {
        "client_id": frontend_client_id,
        "grant_type": "refresh_token",
        "refresh_token": fake_tokens['refresh'],
    }

    response = await test_client.post("/oauth/token/", json=req)
    # res_j = response.json()
    # print(res_j)
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_auth_code(test_client, module_mocker: MockerFixture, mock_get_keys):
    get_flow = module_mocker.patch('dodekaserver.data.kv.get_flow_user')
    get_auth = module_mocker.patch('dodekaserver.data.kv.get_auth_request')
    r_save = module_mocker.patch('dodekaserver.data.refreshtoken.refresh_save')

    def flow_side_effect(kv, code):
        if code == session_key:
            return mock_flow_user

    get_flow.side_effect = flow_side_effect

    def auth_side_effect(kv, flow_id):
        if flow_id == mock_flow_user.flow_id:
            return mock_auth_request

    get_auth.side_effect = auth_side_effect

    r_save.return_value = 44

    verifier = "aIhn-rcznAqlfjvmaX7aS3ZLcmycIGWWnnAFDEn-VLI"
    req = {
        "client_id": frontend_client_id,
        "grant_type": "authorization_code",
        "code": session_key,
        "redirect_uri": mock_redirect,
        "code_verifier": verifier
    }

    response = await test_client.post("/oauth/token/", json=req)
    # res_j = response.json()
    # print(res_j)
    assert response.status_code == 200
