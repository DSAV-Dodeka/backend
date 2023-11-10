import pytest
from pytest_mock import MockerFixture
from starlette.testclient import TestClient

from apiserver.app_def import create_app
from apiserver.app_lifespan import register_and_define_code
from apiserver.data import Source
from apiserver.data.context import Code
from apiserver.env import load_config
from tests.test_resources import res_path
from tests.test_util import mock_lifespan, setup_fake_dsrc


@pytest.fixture(scope="module")
def api_config():
    test_config_path = res_path.joinpath("testenv.toml")
    yield load_config(test_config_path)


@pytest.fixture(scope="module")
def make_dsrc(module_mocker: MockerFixture):
    yield setup_fake_dsrc(module_mocker)


@pytest.fixture(scope="module")
def make_cd():
    cd = register_and_define_code()
    yield cd


@pytest.fixture(scope="module")
def lifespan_fixture(api_config, make_dsrc: Source, make_cd: Code):
    yield mock_lifespan(make_dsrc, api_config, make_cd)


@pytest.fixture(scope="module")
def app(lifespan_fixture):
    # startup, shutdown is not run
    apiserver_app = create_app(lifespan_fixture)
    yield apiserver_app


@pytest.fixture(scope="module")
def test_client(app):
    with TestClient(app=app) as test_client:
        yield test_client
