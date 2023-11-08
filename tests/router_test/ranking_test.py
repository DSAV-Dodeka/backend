from contextlib import asynccontextmanager

import pytest
from faker import Faker
from fastapi import FastAPI
from pytest_mock import MockerFixture
from sqlalchemy.ext.asyncio import AsyncConnection
from starlette.testclient import TestClient

from apiserver.app_def import create_app
from apiserver.app_lifespan import safe_startup, register_and_define_code
from apiserver.data import Source
from apiserver.data.context import Code
from apiserver.data.context.app_context import AuthorizeAppContext, RankingContext
from apiserver.env import load_config
from apiserver.lib.model.entities import User, UserData, UserPointsNames
from test_util import make_test_user, make_base_ud, Fixture
from test_resources import res_path


@pytest.fixture
def gen_user(faker: Faker):
    yield make_test_user(faker)


@pytest.fixture
def gen_ud_u(faker: Faker) -> Fixture[tuple[UserData, User]]:
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


def mock_authrz_ctx():
    class MockAuthorizeAppContext(AuthorizeAppContext):
        @classmethod
        async def require_admin(cls, authorization: str, dsrc: Source) -> bool:
            return True

    return MockAuthorizeAppContext()


def mock_wrap_ctx(point_names: list[UserPointsNames], test_event_id: str):
    class MockWrapContext(RankingContext):
        @classmethod
        async def get_event_user_points(
            cls, dsrc: Source, event_id: str
        ) -> list[UserPointsNames]:
            if event_id == test_event_id:
                return point_names

            return []

    return MockWrapContext()


def test_get_event_users(
    test_client: TestClient, make_cd: Code, gen_ud_u: tuple[UserData, User]
):
    test_ud, test_u = gen_ud_u
    point_names = [
        UserPointsNames.model_validate(
            {
                "user_id": test_u.user_id,
                "firstname": test_ud.firstname,
                "lastname": test_ud.lastname,
                "points": 3,
            }
        ),
        UserPointsNames.model_validate(
            {
                "user_id": "someperson2",
                "firstname": "first2",
                "lastname": "last2",
                "points": 5,
            }
        ),
    ]
    event_id = "some_event"

    make_cd.app_context.rank_ctx = mock_wrap_ctx(point_names, event_id)
    make_cd.app_context.authrz_ctx = mock_authrz_ctx()
    headers = {"Authorization": "something"}
    response = test_client.get(f"/admin/class/users/event/{event_id}/", headers=headers)
    r_json = response.json()
    assert len(r_json) == len(point_names)
    assert r_json[0]["user_id"] == test_u.user_id
    assert r_json[1]["lastname"] == "last2"
