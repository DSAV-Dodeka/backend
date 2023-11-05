from contextlib import asynccontextmanager

import pytest
import tomllib
from faker import Faker
from fastapi import FastAPI
from httpx import codes
from pytest_mock import MockerFixture
from sqlalchemy.ext.asyncio import AsyncConnection
from starlette.testclient import TestClient

from apiserver.app_def import create_app
from apiserver.app_lifespan import State, safe_startup, register_and_define_code
from apiserver.data import Source
from apiserver.data.context import Code
from apiserver.define import DEFINE
from apiserver.env import load_config
from apiserver.lib.model.entities import IdInfo
from auth.core.model import (
    FlowUser,
    AuthRequest,
    KeyState,
    AuthKeys,
    IdInfo as AuthIdInfo,
    RefreshToken,
)
from auth.core.util import utc_timestamp
from auth.data.context import TokenContext
from auth.data.schemad.entities import SavedRefreshToken
from auth.data.schemad.ops import SchemaOps
from auth.define import refresh_exp, id_exp, access_exp
from auth.hazmat.key_decode import aes_from_symmetric
from auth.hazmat.structs import PEMPrivateKey
from datacontext.context import Context
from router_test.test_util import (
    make_test_user,
    mock_auth_request,
    GenUser,
    mock_redirect,
    KeyValues,
    make_extended_test_user,
)
from store import Store
from test_resources import res_path


# @pytest.fixture(scope="session", autouse=True)
# def faker_seed():
#     return 2085203821


@pytest.fixture
def gen_user(faker: Faker):
    yield make_test_user(faker)


@pytest.fixture
def gen_ext_user(faker: Faker):
    yield make_extended_test_user(faker)


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
    async def mock_lifespan(app: FastAPI) -> State:
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


@pytest.fixture
def user_mock_flow_user(gen_user: GenUser):
    mock_flow_id = "abcdmock"
    test_token_scope = "doone"

    yield FlowUser(
        auth_time=utc_timestamp() - 20,
        flow_id=mock_flow_id,
        scope=test_token_scope,
        user_id=gen_user.user_id,
    ), test_token_scope, mock_flow_id, gen_user


@pytest.fixture(scope="module")
def test_values():
    test_values_pth = res_path.joinpath("test_values.toml")
    with open(test_values_pth, "rb") as f:
        test_values_dict = tomllib.load(f)

    yield test_values_dict


@pytest.fixture(scope="module")
def auth_keys(test_values: dict):
    keys = KeyValues.model_validate(test_values["keys"])
    symmetric_key = aes_from_symmetric(keys.symmetric)
    signing_key = PEMPrivateKey(
        kid="sig", public=keys.signing_public, private=keys.signing_private
    )

    yield AuthKeys(
        symmetric=symmetric_key, old_symmetric=symmetric_key, signing=signing_key
    )


def mock_token_code_context(
    test_flow_user: FlowUser,
    test_code: str,
    test_auth_request: AuthRequest,
    test_flow_id: str,
    test_keys: AuthKeys,
    test_refresh_id: int,
    mock_db: dict,
):
    class MockTokenContext(TokenContext):
        @classmethod
        async def pop_flow_user(
            cls, ctx: Context, store: Store, authorization_code: str
        ) -> FlowUser:
            if authorization_code == test_code:
                return test_flow_user

        @classmethod
        async def get_auth_request(
            cls, ctx: Context, store: Store, flow_id: str
        ) -> AuthRequest:
            if flow_id == test_flow_id:
                return test_auth_request

        @classmethod
        async def get_keys(
            cls, ctx: Context, store: Store, key_state: KeyState
        ) -> AuthKeys:
            return test_keys

        @classmethod
        async def get_id_info(
            cls, ctx: Context, store: Store, ops: SchemaOps, user_id: str
        ) -> AuthIdInfo:
            return AuthIdInfo()

        @classmethod
        async def add_refresh_token(
            cls,
            ctx: Context,
            store: Store,
            ops: SchemaOps,
            refresh_save: SavedRefreshToken,
        ) -> int:
            refresh_save.id = test_refresh_id
            mock_db[test_refresh_id] = refresh_save

            return test_refresh_id

    return MockTokenContext


def test_auth_code(
    test_client, make_cd: Code, user_mock_flow_user, auth_keys: AuthKeys
):
    mock_flow_user, test_token_scope, mock_flow_id, test_user = user_mock_flow_user
    code_session_key = "somecomplexsessionkey"
    code_verifier = "NiiCPTK4e73kAVCfWZyZX6AvIXyPg396Q4063oGOI3w"
    test_refresh_id = 88
    mock_db = {}

    make_cd.auth_context.token_ctx = mock_token_code_context(
        mock_flow_user,
        code_session_key,
        mock_auth_request,
        mock_flow_id,
        auth_keys,
        test_refresh_id,
        mock_db,
    )

    req = {
        "client_id": DEFINE.frontend_client_id,
        "grant_type": "authorization_code",
        "code": code_session_key,
        "redirect_uri": mock_redirect,
        "code_verifier": code_verifier,
    }

    response = test_client.post("/oauth/token/", json=req)

    assert response.status_code == codes.OK
    saved_refresh = mock_db[test_refresh_id]
    assert isinstance(saved_refresh, SavedRefreshToken)
    assert saved_refresh.user_id == test_user.user_id


def fake_tokens(
    test_user: GenUser,
    test_id_info: IdInfo,
    test_scope: str,
    test_token_id: int,
    keys: AuthKeys,
):
    from auth.token.build import finish_tokens
    from auth.token.build import create_tokens

    utc_now = utc_timestamp()
    auth_time = utc_now
    access_token_data, id_token_data, access_scope, refresh_save = create_tokens(
        test_user.user_id,
        test_scope,
        auth_time,
        mock_auth_request.nonce,
        utc_now,
        test_id_info,
        DEFINE.issuer,
        DEFINE.frontend_client_id,
        DEFINE.backend_client_id,
        refresh_exp,
    )

    refresh_token, access_token, id_token = finish_tokens(
        test_token_id,
        refresh_save,
        keys.symmetric,
        access_token_data,
        id_token_data,
        test_id_info,
        utc_now,
        keys.signing,
        access_exp,
        id_exp,
        nonce="",
    )

    return refresh_token, refresh_save


def mock_token_refresh_context(
    test_keys: AuthKeys,
    test_refresh_token: SavedRefreshToken,
    new_refresh_id: int,
    mock_db: dict,
):
    class MockTokenContext(TokenContext):
        @classmethod
        async def get_keys(
            cls, ctx: Context, store: Store, key_state: KeyState
        ) -> AuthKeys:
            return test_keys

        @classmethod
        async def get_saved_refresh(
            cls, ctx: Context, store: Store, ops: SchemaOps, old_refresh: RefreshToken
        ) -> SavedRefreshToken:
            return mock_db[old_refresh.id]

        @classmethod
        async def replace_refresh(
            cls,
            ctx: Context,
            store: Store,
            ops: SchemaOps,
            old_refresh_id: int,
            new_refresh_save: SavedRefreshToken,
        ) -> int:
            if old_refresh_id == test_refresh_token.id:
                new_refresh_save.id = new_refresh_id
                mock_db[new_refresh_id] = new_refresh_save
                return new_refresh_id

    return MockTokenContext


def test_refresh(test_client, make_cd: Code, gen_ext_user, auth_keys: AuthKeys):
    test_user, test_id_info = gen_ext_user
    test_scope = "itest refresh"
    test_refresh_id = 48
    refresh_val, refresh_save = fake_tokens(
        test_user, test_id_info, test_scope, test_refresh_id, auth_keys
    )
    refresh_save.id = test_refresh_id
    new_refresh_id = 50
    mock_db = {test_refresh_id: refresh_save}

    make_cd.auth_context.token_ctx = mock_token_refresh_context(
        auth_keys, refresh_save, new_refresh_id, mock_db
    )

    req = {
        "client_id": DEFINE.frontend_client_id,
        "grant_type": "refresh_token",
        "refresh_token": refresh_val,
    }

    response = test_client.post("/oauth/token/", json=req)
    # res_j = response.json()
    # print(res_j)
    assert response.status_code == codes.OK
    new_saved_refresh = mock_db[new_refresh_id]
    assert isinstance(new_saved_refresh, SavedRefreshToken)
    assert new_saved_refresh.id == new_refresh_id
