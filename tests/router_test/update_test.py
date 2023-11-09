from typing import Optional

import pytest
from faker import Faker
from httpx import codes

from apiserver.data import Source
from apiserver.data.context import Code, UpdateContext
from apiserver.lib.model.entities import UserData, User
from tests.test_util import (
    make_test_user,
    make_base_ud,
)


@pytest.fixture
def gen_user(faker: Faker):
    yield make_test_user(faker)


@pytest.fixture
def gen_ud_u(faker: Faker):
    yield make_base_ud(faker)


pytest_plugins = [
    "tests.router_test.data_fixtures",
]


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
