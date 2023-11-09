import pytest
from faker import Faker
from httpx import codes
from starlette.testclient import TestClient
from yarl import URL

from apiserver.data.context import Code
from auth.core.model import AuthRequest
from auth.data.context import AuthorizeContext
from tests.test_util import make_test_user, mock_auth_request
from store import Store
from store.error import NoDataError

pytest_plugins = [
    "tests.router_test.data_fixtures",
]


@pytest.fixture
def gen_user(faker: Faker):
    yield make_test_user(faker)


def mock_oauth_start_context(test_flow_id: str, req_store: dict):
    class MockAuthorizeContext(AuthorizeContext):
        @classmethod
        async def store_auth_request(cls, store: Store, auth_request: AuthRequest):
            req_store[test_flow_id] = auth_request

            return test_flow_id

    return MockAuthorizeContext()


def test_oauth_authorize(test_client: TestClient, make_cd: Code):
    req_store = {}
    flow_id = "af60854e11352c9fb02f738a888710c8"

    make_cd.auth_context.authorize_ctx = mock_oauth_start_context(flow_id, req_store)

    req = {
        "response_type": "code",
        "client_id": "dodekaweb_client",
        "redirect_uri": "https://dsavdodeka.nl/auth/callback",
        "state": "KV6A2hTOv6mOFYVpTAOmWw",
        "code_challenge": "8LNMS54GS7iB7H67U5OFLclCl0F87vy5uf-Izj3TCdQ",
        "code_challenge_method": "S256",
        "nonce": "eB2lpr1IqZdJzt9CfDZ5jrHGa6yE87UUTFd4CWweOI",
    }

    response = test_client.get("/oauth/authorize/", params=req, follow_redirects=False)

    assert response.status_code == codes.SEE_OTHER
    assert isinstance(req_store[flow_id], AuthRequest)
    # TODO test validate function in unit test
    next_req = response.next_request
    assert next_req is not None
    assert next_req.url.query == f"flow_id={flow_id}".encode("utf-8")


def mock_oauth_callback_context(test_flow_id: str, test_auth_request: AuthRequest):
    class MockAuthorizeContext(AuthorizeContext):
        @classmethod
        async def get_auth_request(cls, store: Store, flow_id: str) -> AuthRequest:
            if flow_id == test_flow_id:
                return test_auth_request
            raise NoDataError("Test no exist", "test_empty")

    return MockAuthorizeContext()


def test_oauth_callback(test_client: TestClient, make_cd: Code):
    test_flow_id = "1cd7afeca7eb420201ea69e06d9085ae2b8dd84adaae8d27c89746aab75d1dff"
    test_code = "zySjwa5CpddMzSydqKOvXZHQrtRK-VD83aOPMAB_1gEVxSscBywmS8XxZze3letN9whXUiRfSEfGel9e-5XGgQ"

    req = {
        "flow_id": test_flow_id,
        "code": test_code,
    }

    make_cd.auth_context.authorize_ctx = mock_oauth_callback_context(
        test_flow_id, mock_auth_request
    )

    response = test_client.get("/oauth/callback/", params=req, follow_redirects=False)

    assert response.status_code == codes.SEE_OTHER
    next_req = response.next_request
    assert next_req is not None
    parsed = URL(str(next_req.url))
    assert parsed.query.get("code") == test_code
    assert parsed.query.get("state") == mock_auth_request.state
