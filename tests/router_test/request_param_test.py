from httpx import codes
from starlette.testclient import TestClient

from apiserver.define import DEFINE


pytest_plugins = [
    "tests.router_test.data_fixtures",
]


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
