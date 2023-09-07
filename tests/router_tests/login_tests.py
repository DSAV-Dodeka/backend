from dataclasses import dataclass
from pathlib import Path

import pytest
from pytest_mock import MockerFixture

from apiserver.env import load_config
from apiserver.lib.utilities import gen_id_name
from faker import Faker


def cr_user_id(id_int: int, g_id_name: str):
    return f"{id_int}_{g_id_name}"


@pytest.fixture(scope="session", autouse=True)
def faker_seed():
    return 2085203821


@dataclass
class TestUser:
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

    yield TestUser(user_id=test_user_id, user_email=test_user_email)


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
