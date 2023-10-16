from contextlib import asynccontextmanager

import pytest
from fastapi import FastAPI
from httpx import codes
from pytest_mock import MockerFixture
from sqlalchemy.ext.asyncio import AsyncConnection
from starlette.testclient import TestClient

from apiserver.app_def import create_app
from apiserver.app_lifespan import safe_startup, State, register_and_define_code
from apiserver.data import Source
from apiserver.data.frame import Code
from apiserver.define import DEFINE
from apiserver.env import load_config
from test_resources import res_path


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
    cd = register_and_define_code()
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
    assert res_j["debug_key"] == "invalid_auth_code_token_request"


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
    assert res_j["debug_key"] == "invalid_auth_code_token_request"


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
    assert res_j["debug_key"] == "invalid_auth_code_token_request"
