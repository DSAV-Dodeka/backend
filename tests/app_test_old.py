import asyncio
from contextlib import asynccontextmanager
from datetime import date
from pathlib import Path
from urllib.parse import urlparse, parse_qs

import pytest
from fastapi import status, FastAPI
from fastapi.testclient import TestClient
from httpx import codes
from pytest_mock import MockerFixture
from sqlalchemy.ext.asyncio import AsyncConnection

from apiserver.define import (
    DEFINE,
    refresh_exp,
    access_exp,
    id_exp,
)
from apiserver.app_def import State, safe_startup, create_app
from apiserver.lib.utilities import gen_id_name
from apiserver.data import Source
from apiserver.data import ops

from apiserver.lib.model.entities import (
    UserData,
    User,
    SavedState,
    AuthRequest,
)
from auth.data.schemad.entities import SavedRefreshToken
from auth.hazmat.structs import A256GCMKey, PEMPrivateKey
from auth.core.model import SavedRegisterState, FlowUser
from apiserver.env import load_config
from auth.core.util import utc_timestamp
from auth.hazmat.key_decode import aes_from_symmetric


@pytest.fixture(scope="module")
def event_loop():
    """Necessary for async tests with module-scoped fixtures"""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="module")
def api_config():
    test_config_path = Path(__file__).parent.joinpath("testenv.toml")
    yield load_config(test_config_path)


@pytest.fixture(scope="module")
def lifespan_fixture(api_config, module_mocker: MockerFixture):
    dsrc_inst = Source()
    store_mock = module_mocker.MagicMock(spec=dsrc_inst.store)
    store_mock.db.connect = module_mocker.MagicMock(
        return_value=module_mocker.MagicMock(spec=AsyncConnection)
    )
    dsrc_inst.store = store_mock
    safe_startup(dsrc_inst, api_config)

    @asynccontextmanager
    async def mock_lifespan(app: FastAPI) -> State:
        yield {"config": api_config, "dsrc": dsrc_inst}

    yield mock_lifespan


@pytest.fixture(scope="module")
def app(lifespan_fixture):
    # startup, shutdown is not run
    apiserver_app = create_app(lifespan_fixture)
    yield apiserver_app


@pytest.fixture(scope="module")
def test_client(app):
    with TestClient(app=app) as test_client:
        yield test_client


def test_root(test_client):
    response = test_client.get("/")

    assert response.status_code == codes.OK
    assert response.json() == {"Hallo": "Atleten"}


def test_incorrect_client_id(test_client: TestClient):
    req = {
        "client_id": "incorrect",
        "grant_type": "",
        "code": "",
        "redirect_uri": "",
        "code_verifier": "",
        "refresh_token": "",
    }
    response = test_client.post("/oauth/token/", json=req)
    assert response.status_code == codes.BAD_REQUEST
    assert response.json()["error"] == "invalid_client"


def test_incorrect_grant_type(test_client: TestClient):
    req = {
        "client_id": DEFINE.frontend_client_id,
        "grant_type": "wrong",
        "code": "",
        "redirect_uri": "",
        "code_verifier": "",
        "refresh_token": "",
    }

    response = test_client.post("/oauth/token/", json=req)
    assert response.status_code == codes.BAD_REQUEST
    res_j = response.json()
    assert res_j["error"] == "unsupported_grant_type"


def test_empty_verifier(test_client: TestClient):
    req = {
        "client_id": DEFINE.frontend_client_id,
        "grant_type": "authorization_code",
        "code": "some",
        "redirect_uri": "some",
        "code_verifier": "",
        "refresh_token": "",
    }

    response = test_client.post("/oauth/token/", json=req)
    assert response.status_code == codes.BAD_REQUEST
    res_j = response.json()
    assert res_j["error"] == "invalid_request"
    assert res_j["debug_key"] == "incomplete_code"


def test_missing_redirect(test_client: TestClient):
    req = {
        "client_id": DEFINE.frontend_client_id,
        "grant_type": "authorization_code",
        "code": "some",
        "code_verifier": "some",
        "refresh_token": "",
    }

    response = test_client.post("/oauth/token/", json=req)
    assert response.status_code == codes.BAD_REQUEST
    res_j = response.json()
    assert res_j["error"] == "invalid_request"
    assert res_j["debug_key"] == "incomplete_code"


def test_empty_code(test_client: TestClient):
    req = {
        "client_id": DEFINE.frontend_client_id,
        "grant_type": "authorization_code",
        "code": "",
        "redirect_uri": "some",
        "code_verifier": "some",
        "refresh_token": "",
    }

    response = test_client.post("/oauth/token/", json=req)
    assert response.status_code == codes.BAD_REQUEST
    res_j = response.json()
    assert res_j["error"] == "invalid_request"
    assert res_j["debug_key"] == "incomplete_code"


mock_symm_key = {
    "id": 2,
    "algorithm": "symmetric",
    "public": None,
    "private": "8T3oEm_haJZbn6xu-klttJXk5QBPYlurQrqA5SDx-Ck",
    "public_format": None,
    "public_encoding": None,
    "private_format": "none",
    "private_encoding": "base64url",
}
mock_token_key = {
    "id": 1,
    "algorithm": "ed448",
    "public": (
        "-----BEGIN PUBLIC"
        " KEY-----\nMEMwBQYDK2VxAzoAtPGddEupA3b5P5yr9gT3rvjzWeQH5cedY6RcwN3A5zTS9n8C\nc6dOR+XUPVLVu0o0i/t46fW1HMQA\n-----END"
        " PUBLIC KEY-----\n"
    ),
    "private": (
        "-----BEGIN PRIVATE"
        " KEY-----\nMEcCAQAwBQYDK2VxBDsEOY1wa98ZvsK8pYML+ICD9Mbtavr+QC5PC301oVn5jPM6\nT8tECKaZvu5mxG/OfxlEKxl/XIKuClP1mw==\n-----END"
        " PRIVATE KEY-----\n"
    ),
    "public_format": "X509PKCS#1",
    "public_encoding": "PEM",
    "private_format": "PKCS#8",
    "private_encoding": "PEM",
}


@pytest.fixture
def mock_get_keys(mocker: MockerFixture):
    get_k_s = mocker.patch("auth.data.keys.get_symmetric_key")
    get_k_s.return_value = A256GCMKey(kid="b", symmetric=mock_symm_key["private"])
    get_k_p = mocker.patch("auth.data.keys.get_pem_private_key")
    get_k_p.return_value = PEMPrivateKey(
        kid="a", public=mock_token_key["public"], private=mock_token_key["private"]
    )


def cr_user_id(id_int: int, g_id_name: str):
    return f"{id_int}_{g_id_name}"


code_session_key = "somecomplexsessionkey"
mock_redirect = "http://localhost:3000/auth/callback"
mock_flow_id = "1d5c621ea3a2da319fe0d0a680046fd6369a60e450ff04f59c51b0bfb3d96eef"
fake_token_scope = "test"
mock_user_id_int = 20
mock_user_id_fn = "mr"
mock_user_id_ln = "lastmocker"
mock_user_email = "mr@mocker.nl"
mock_user_id_name = gen_id_name(mock_user_id_fn, mock_user_id_ln)
mock_user_id = cr_user_id(mock_user_id_int, mock_user_id_name)
mock_flow_user = FlowUser(
    auth_time=utc_timestamp() - 20,
    flow_id=mock_flow_id,
    scope=fake_token_scope,
    user_id=mock_user_id,
)
mock_userdata = UserData(
    user_id=mock_user_id,
    active=True,
    firstname="Test",
    lastname="Register",
    email=mock_user_email,
    phone="06",
    av40id=123,
    joined=date.today(),
    registered=False,
    showage=False,
)
mock_auth_request = AuthRequest(
    response_type="code",
    client_id="dodekaweb_client",
    redirect_uri=mock_redirect,
    state="KV6A2hTOv6mOFYVpTAOmWw",
    code_challenge="8LNMS54GS7iB7H67U5OFLclCl0F87vy5uf-Izj3TCdQ",
    code_challenge_method="S256",
    nonce="-eB2lpr1IqZdJzt9CfDZ5jrHGa6yE87UUTFd4CWweOI",
)
nonce_original = "6SWk9T1sUfqgSYeq2XlawA"
code_verifier = "NiiCPTK4e73kAVCfWZyZX6AvIXyPg396Q4063oGOI3w"

fake_token_id = 44


@pytest.fixture
def req_store(store_fix, mocker: MockerFixture):
    r_store = mocker.patch("auth.data.authorize.store_auth_request")

    def store_side_effect(f_store, req):
        store_fix[mock_flow_id] = req
        return mock_flow_id

    r_store.side_effect = store_side_effect

    yield store_fix
