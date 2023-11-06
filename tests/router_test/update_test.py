from contextlib import asynccontextmanager
from typing import Optional

import pytest
from faker import Faker
from fastapi import FastAPI
from httpx import codes
from pytest_mock import MockerFixture
from sqlalchemy.ext.asyncio import AsyncConnection
from starlette.testclient import TestClient

from apiserver.app_def import create_app
from apiserver.app_lifespan import State, safe_startup, register_and_define_code
from apiserver.data import Source
from apiserver.data.context import Code, UpdateContext
from apiserver.env import load_config
from apiserver.lib.model.entities import UserData, User
from datacontext.context import Context
from router_test.test_util import (
    make_test_user,
    make_base_ud,
)
from test_resources import res_path


@pytest.fixture
def gen_user(faker: Faker):
    yield make_test_user(faker)


@pytest.fixture
def gen_ud_u(faker: Faker):
    yield make_base_ud(faker)


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
    async def mock_lifespan(app: FastAPI):
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


def mock_update_ctx(
    mock_db: dict[str, UserData], mock_kv: dict[str, str], mock_flow_id: str
):
    class MockUpdateContext(UpdateContext):
        @classmethod
        async def store_email_flow_password_change(
            cls, dsrc: Source, email: str
        ) -> Optional[str]:
            ud = mock_db.get(email)
            if ud is None:
                return None
            mock_kv[mock_flow_id] = email

            return mock_flow_id

    return MockUpdateContext()


def test_update_register_exists(
    test_client,
    gen_ud_u: tuple[UserData, User],
    make_cd: Code,
):
    test_ud, test_u = gen_ud_u
    test_flow_id = "a3a2894291ab408d95d7e3cde62d0f06da22b86bd49c2a34231123ed4b5e877e"
    mock_db = {test_ud.email: test_ud}
    mock_kv = {}

    make_cd.app_context.update_ctx = mock_update_ctx(mock_db, mock_kv, test_flow_id)

    req = {"email": test_ud.email}

    response = test_client.post("/update/password/reset/", json=req)
    assert response.status_code == codes.OK
    assert mock_kv[test_flow_id] == test_ud.email


def test_update_register_not_exists(
    test_client,
    gen_ud_u: tuple[UserData, User],
    make_cd: Code,
):
    test_ud, test_u = gen_ud_u
    test_flow_id = "a3a2894291ab408d95d7e3cde62d0f06da22b86bd49c2a34231123ed4b5e877e"
    mock_db = {}
    mock_kv = {}

    make_cd.app_context.update_ctx = mock_update_ctx(mock_db, mock_kv, test_flow_id)

    req = {"email": test_ud.email}

    response = test_client.post("/update/password/reset/", json=req)
    assert response.status_code == codes.OK
    assert mock_kv.get(test_flow_id) is None
