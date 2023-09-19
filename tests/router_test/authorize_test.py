from contextlib import asynccontextmanager

import pytest
from faker import Faker
from fastapi import FastAPI
from httpx import codes
from pytest_mock import MockerFixture
from sqlalchemy.ext.asyncio import AsyncConnection
from starlette.testclient import TestClient
from yarl import URL

from apiserver.app_def import create_app
from apiserver.app_lifespan import State, safe_startup, define_code
from apiserver.data import Source
from apiserver.data.frame import Code
from apiserver.env import load_config
from auth.core.model import AuthRequest
from auth.data.context import AuthorizeContext
from router_test.test_util import make_test_user, mock_auth_request
from store import Store
from test_resources import res_path


@pytest.fixture
def gen_user(faker: Faker):
    yield make_test_user(faker)


@pytest.fixture(scope="module")
def api_config():
    test_config_path = res_path.joinpath("testenv.toml")
    yield load_config(test_config_path)


@pytest.fixture(scope="module")
def make_dsrc(module_mocker: MockerFixture):
    dsrc_inst = Source()
    store_mock = module_mocker.MagicMock(spec=dsrc_inst.store)
    store_mock.db.connect = module_mocker.MagicMock(
        return_value=module_mocker.MagicMock(spec=AsyncConnection)
    )
    dsrc_inst.store = store_mock

    yield dsrc_inst


@pytest.fixture(scope="module")
def make_cd():
    cd = define_code()
    yield cd


@pytest.fixture(scope="module")
def lifespan_fixture(api_config, make_dsrc: Source, make_cd: Code):
    safe_startup(make_dsrc, api_config)

    @asynccontextmanager
    async def mock_lifespan(app: FastAPI) -> State:
        yield {"dsrc": make_dsrc, "cd": make_cd}

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


def mock_oauth_start_context(test_flow_id: str, req_store: dict):
    class MockAuthorizeContext(AuthorizeContext):
        @classmethod
        async def store_auth_request(cls, store: Store, auth_request: AuthRequest):
            req_store[test_flow_id] = auth_request

            return test_flow_id

    return MockAuthorizeContext


def test_oauth_authorize(test_client: TestClient, make_cd: Code):
    req_store = {}
    flow_id = "af60854e11352c9fb02f738a888710c8"

    make_cd.context.authorize_ctx = mock_oauth_start_context(flow_id, req_store)

    req = {
        "response_type": "code",
        "client_id": "dodekaweb_client",
        "redirect_uri": "https://dsavdodeka.nl/auth/callback",
        "state": "KV6A2hTOv6mOFYVpTAOmWw",
        "code_challenge": "8LNMS54GS7iB7H67U5OFLclCl0F87vy5uf-Izj3TCdQ",
        "code_challenge_method": "S256",
        "nonce": "eB2lpr1IqZdJzt9CfDZ5jrHGa6yE87UUTFd4CWweOI",
    }

    response = test_client.get("/oauth/authorize/", params=req, follow_redirects=False)

    assert response.status_code == codes.SEE_OTHER
    assert isinstance(req_store[flow_id], AuthRequest)
    # TODO test validate function in unit test
    assert response.next_request.url.query == f"flow_id={flow_id}".encode("utf-8")


def mock_oauth_callback_context(test_flow_id: str, test_auth_request: AuthRequest):
    class MockAuthorizeContext(AuthorizeContext):
        @classmethod
        async def get_auth_request(cls, store: Store, flow_id: str) -> AuthRequest:
            if flow_id == test_flow_id:
                return test_auth_request

    return MockAuthorizeContext


def test_oauth_callback(test_client: TestClient, make_cd: Code):
    test_flow_id = "1cd7afeca7eb420201ea69e06d9085ae2b8dd84adaae8d27c89746aab75d1dff"
    test_code = "zySjwa5CpddMzSydqKOvXZHQrtRK-VD83aOPMAB_1gEVxSscBywmS8XxZze3letN9whXUiRfSEfGel9e-5XGgQ"

    req = {
        "flow_id": test_flow_id,
        "code": test_code,
    }

    make_cd.context.authorize_ctx = mock_oauth_callback_context(
        test_flow_id, mock_auth_request
    )

    response = test_client.get("/oauth/callback/", params=req, follow_redirects=False)

    assert response.status_code == codes.SEE_OTHER
    parsed = URL(str(response.next_request.url))
    assert parsed.query.get("code") == test_code
    assert parsed.query.get("state") == mock_auth_request.state
