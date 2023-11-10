from typing import Optional
from fastapi.testclient import TestClient

import pytest
from faker import Faker
from httpx import codes

from apiserver.data import Source
from apiserver.data.context import Code, UpdateContext
from apiserver.lib.model.entities import UserData, User
from auth.core.model import FlowUser
from auth.core.util import utc_timestamp
from auth.data.context import LoginContext
from store import Store
from store.error import NoDataError
from tests.test_util import (
    GenUser,
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


def mock_delete_login_ctx(
    pw_user_id: str,
    test_auth_code: str,
    pw_flow_id: str,
    delete_flow_id: str,
    delete_test_user_id: str,
    deleted_users: set[str],
):
    class MockLoginContext(LoginContext):
        @classmethod
        async def pop_flow_user(cls, store: Store, authorization_code: str) -> FlowUser:
            if authorization_code == test_auth_code:
                utc_now = utc_timestamp()

                return FlowUser(
                    user_id=pw_user_id,
                    scope="some",
                    flow_id=pw_flow_id,
                    auth_time=utc_now - 10,
                )

            raise NoDataError("No test data", "no_test_data")

    class MockUpdateContext(UpdateContext):
        @classmethod
        async def pop_string(cls, dsrc: Source, key: str) -> Optional[str]:
            if key == delete_flow_id:
                return delete_test_user_id

            return None

        @classmethod
        async def delete_user(cls, dsrc: Source, user_id: str) -> None:
            deleted_users.add(user_id)

    return MockLoginContext(), MockUpdateContext()


def test_delete_account_check(
    test_client: TestClient,
    gen_user: GenUser,
    make_cd: Code,
):
    test_auth_code = "b0c502c562c99b0bc7a8dbe8a1db8718"
    test_flow_id = "881c2927dbda95a16440e5bb06372706"
    deleted_users = set()
    mock_login_ctx, mock_update_ctx = mock_delete_login_ctx(
        gen_user.user_id,
        test_auth_code,
        test_flow_id,
        test_flow_id,
        gen_user.user_id,
        deleted_users,
    )

    make_cd.auth_context.login_ctx = mock_login_ctx
    make_cd.app_context.update_ctx = mock_update_ctx

    req = {"flow_id": test_flow_id, "code": test_auth_code}

    response = test_client.post("/update/delete/check/", json=req)
    assert response.status_code == codes.OK
    assert gen_user.user_id in deleted_users


def test_delete_account_mismatch(
    test_client: TestClient,
    gen_user: GenUser,
    make_cd: Code,
    faker: Faker,
):
    test_auth_code = "b0c502c562c99b0bc7a8dbe8a1db8718"
    pw_flow_id = "881c2927dbda95a16440e5bb06372706"
    delete_flow_id = "5f168a449f03c4a40d104bd1a43e654c"
    pw_flow_user = make_test_user(faker)
    deleted_users = set()
    mock_login_ctx, mock_update_ctx = mock_delete_login_ctx(
        pw_flow_user.user_id,
        test_auth_code,
        pw_flow_id,
        delete_flow_id,
        gen_user.user_id,
        deleted_users,
    )

    make_cd.auth_context.login_ctx = mock_login_ctx
    make_cd.app_context.update_ctx = mock_update_ctx

    # Scenario in which someone requested a delete using stolen access token
    # Then logs in as themselves and provides their own auth code
    req = {"flow_id": delete_flow_id, "code": test_auth_code}

    response = test_client.post("/update/delete/check/", json=req)
    print(response.json())
    assert response.status_code == codes.BAD_REQUEST
    assert response.json()["debug_key"] == "update_flows_dont_match"
    assert not deleted_users
