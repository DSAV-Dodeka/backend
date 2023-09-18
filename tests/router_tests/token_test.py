from contextlib import asynccontextmanager

import pytest
from faker import Faker
from fastapi import FastAPI
from httpx import codes
from pytest_mock import MockerFixture
from sqlalchemy.ext.asyncio import AsyncConnection
from starlette.testclient import TestClient

from apiserver.app_def import create_app
from apiserver.app_lifespan import State, safe_startup
from apiserver.data import Source
from apiserver.define import DEFINE
from apiserver.env import load_config
from auth.core.model import FlowUser
from auth.core.util import utc_timestamp
from router_tests.test_util import (
    make_test_user,
    mock_auth_request,
    TestUser,
    mock_redirect,
)
from test_resources import res_path


# @pytest.fixture(scope="session", autouse=True)
# def faker_seed():
#     return 2085203821


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
def lifespan_fixture(api_config, make_dsrc: Source):
    safe_startup(make_dsrc, api_config)

    @asynccontextmanager
    async def mock_lifespan(app: FastAPI) -> State:
        yield {"dsrc": make_dsrc}

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


@pytest.fixture
def user_mock_flow_user(gen_user: TestUser):
    mock_flow_id = "abcdmock"
    test_token_scope = "doone"

    yield FlowUser(
        auth_time=utc_timestamp() - 20,
        flow_id=mock_flow_id,
        scope=test_token_scope,
        user_id=gen_user.user_id,
    ), test_token_scope, mock_flow_id, gen_user


def test_auth_code(test_client, user_mock_flow_user):
    mock_flow_user, test_token_scope, mock_flow_id, test_user = user_mock_flow_user
    code_session_key = "somecomplexsessionkey"
    code_verifier = "NiiCPTK4e73kAVCfWZyZX6AvIXyPg396Q4063oGOI3w"

    def flow_side_effect(f_dsrc, code):
        if code == code_session_key:
            return mock_flow_user

    get_flow.side_effect = flow_side_effect

    def auth_side_effect(f_dsrc, flow_id):
        if flow_id == mock_flow_user.flow_id:
            return mock_auth_request

    get_auth.side_effect = auth_side_effect

    def ud_side_effect(conn, u_id):
        if u_id == mock_flow_user.user_id:
            return mock_userdata

    get_ud.side_effect = ud_side_effect

    r_save.return_value = 44

    req = {
        "client_id": DEFINE.frontend_client_id,
        "grant_type": "authorization_code",
        "code": code_session_key,
        "redirect_uri": mock_redirect,
        "code_verifier": code_verifier,
    }

    response = test_client.post("/oauth/token/", json=req)
    # res_j = response.json()
    # print(res_j)
    assert response.status_code == codes.OK
