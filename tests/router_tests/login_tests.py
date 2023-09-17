from contextlib import asynccontextmanager
from dataclasses import dataclass
from pathlib import Path

import pytest
from fastapi import FastAPI
from httpx import codes
from pytest_mock import MockerFixture
from sqlalchemy.ext.asyncio import AsyncConnection
from starlette.testclient import TestClient

from apiserver.app_def import create_app
from apiserver.app_lifespan import State, safe_startup
from apiserver.data import Source
from apiserver.env import load_config
from apiserver.lib.utilities import gen_id_name
from faker import Faker

from auth.core.model import SavedState
from auth.data.context import LoginContext
from auth.data.schemad.user import UserOps
from store import Store


def cr_user_id(id_int: int, g_id_name: str):
    return f"{id_int}_{g_id_name}"


@pytest.fixture(scope="session", autouse=True)
def faker_seed():
    return 2085203821


@dataclass
class TestUser:
    id_int: int
    user_id: str
    user_email: str


@pytest.fixture
def gen_user(faker: Faker):
    user_fn = faker.first_name()
    user_ln = faker.last_name()
    test_user_id_int = faker.random_int(min=3, max=300)
    test_id_name = gen_id_name(user_fn, user_ln)
    test_user_id = cr_user_id(test_user_id_int, test_id_name)
    test_user_email = faker.email()

    yield TestUser(
        id_int=test_user_id_int, user_id=test_user_id, user_email=test_user_email
    )


@pytest.fixture(scope="module")
def api_config():
    test_config_path = Path(__file__).parent.joinpath("testenv.toml")
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


def test_root(test_client):
    response = test_client.get("/")

    assert response.status_code == codes.OK
    assert response.json() == {"Hallo": "Atleten"}


mock_opq_setup = {
    "id": 0,
    "value": "pd32VP-D21oNgNId22WdbEiUn5vUeFNhgNReuAv2FQvT8kyBZu9gW2kBn8E60HgbAEHDT6KCy575MVIzgLJQ2daSp_2XpESlXFbsxftf6Bw0_RYzAOZ1YL2Dnrtq1MwOF4jzOi3gs3bHnS_odl9VpaXz4GjQTT7aol5CYB0yYgE",
}


def make_login_context(test_user_id: str, pw_file: str):
    class MockLoginContext(LoginContext):
        @classmethod
        async def get_apake_setup(cls, store: Store) -> str:
            return mock_opq_setup["value"]

        @classmethod
        async def get_user_auth_data(
            cls, store: Store, user_ops: UserOps, login_mail: str
        ) -> tuple[str, str, str, str]:
            return test_user_id, "none", pw_file, "c"

        @classmethod
        async def store_auth_state(
            cls, store: Store, auth_id: str, state: SavedState
        ) -> None:
            pass

    return MockLoginContext


def test_login(test_client, make_dsrc, gen_user: TestUser):
    fake_password_file = "GLgWMaiuTTs2NyK9gvrhbtUMTrHLy2erbEwPnzwFDQ6i5EuUyWEN9yqEarTqxprZ205gkQoY_yks3-1jr3XuTfKfh1byl9LZHFpDA-FWNyc5wV5CBYz_jzruanzI-yFCPt7fPglNFs7mnwPbZaraoKMJX5prMMrULtDF4KlZuv2szqISaM3d9kiVUEgXzNAPh6EMuN1GCySL8gimFyfZxfrk3QCeQJKudx2YZYz9ReBs7EkmAwTCHxeiCmYaDdlu"
    correct_password_file = "6sr_nvpqPqB-GCjj091vbsIsKYdHX2BE_9ICHT-8o329Wn_-9F4gCjfFD1GsPGayGF1oJ2FzyZXLzUS-MmaHO2pTGoD_QyGBiIV9s7LBYxFM_fciaaI08ZahLfj4kmXJfzqcWVSecc7uqgzR5DVamDHlmQUOT6QjXcDmbuPm8eDu1hBdD65ZWmpUz16DK3-k6uBLjQ1fKYj8o3xBShhRQCKpm0PFCjk4uABkXgdzy5EWoKkTZ8cslYe450nAdOqv"

    make_dsrc.context.login_context = make_login_context(
        gen_user.user_id, correct_password_file
    )

    req = {
        "email": gen_user.user_email,
        "client_request": "ht_LfPlozB5sa76eflmWeulgGU4dU4aeEutzyDMTkRoB3bO62RP95nc1PWt6IdJxpiuMW5OsoWEWNpa4EUZrxqAB8a5mLVLBQ81Y-30YlSgppQNdWAgeA-amu93cEisx",
    }

    response = test_client.post("/login/start/", json=req)

    assert response.status_code == codes.OK
