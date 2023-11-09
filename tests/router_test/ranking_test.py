from httpx import codes
import pytest
from faker import Faker
from starlette.testclient import TestClient

from apiserver.data import Source
from apiserver.data.context import Code
from apiserver.data.context.app_context import AuthorizeAppContext, RankingContext
from apiserver.lib.model.entities import AccessToken, User, UserData, UserPointsNames
from tests.test_util import acc_token_from_info, make_test_user, make_base_ud, Fixture


@pytest.fixture
def gen_user(faker: Faker):
    yield make_test_user(faker)


@pytest.fixture
def gen_ud_u(faker: Faker) -> Fixture[tuple[UserData, User]]:
    yield make_base_ud(faker)


pytest_plugins = [
    "tests.router_test.data_fixtures",
]


def mock_authrz_ctx(acc_token: AccessToken):
    class MockAuthorizeAppContext(AuthorizeAppContext):
        @classmethod
        async def verify_token_header(
            cls, authorization: str, dsrc: Source
        ) -> AccessToken:
            return acc_token

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
    acc_token = acc_token_from_info("1_admin", "admin member")

    make_cd.app_context.rank_ctx = mock_wrap_ctx(point_names, event_id)
    make_cd.app_context.authrz_ctx = mock_authrz_ctx(acc_token)
    headers = {"Authorization": "something"}
    response = test_client.get(f"/admin/class/users/event/{event_id}/", headers=headers)
    r_json = response.json()
    assert response.status_code == codes.OK
    assert isinstance(r_json, list)
    assert len(r_json) == len(point_names)
    assert r_json[0]["user_id"] == test_u.user_id
    assert r_json[1]["lastname"] == "last2"
