import asyncio
from contextlib import asynccontextmanager
from datetime import date
from pathlib import Path
from urllib.parse import urlparse, parse_qs

import pytest
from fastapi import status, FastAPI
from fastapi.testclient import TestClient
from httpx import codes
from pytest_mock import MockerFixture
from sqlalchemy.ext.asyncio import AsyncConnection

from apiserver.define import (
    DEFINE,
    refresh_exp,
    access_exp,
    id_exp,
)
from apiserver.app_def import State, safe_startup, create_app
from apiserver.lib.utilities import gen_id_name
from apiserver.data import Source
from apiserver.data import ops

from apiserver.lib.model.entities import (
    UserData,
    User,
    SavedState,
    AuthRequest,
)
from auth.data.schemad.entities import SavedRefreshToken
from auth.hazmat.structs import A256GCMKey, PEMPrivateKey
from auth.core.model import SavedRegisterState, FlowUser
from apiserver.env import load_config
from auth.core.util import utc_timestamp
from auth.hazmat.key_decode import aes_from_symmetric


@pytest.fixture(scope="module")
def event_loop():
    """Necessary for async tests with module-scoped fixtures"""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


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
    assert res_j["debug_key"] == "incomplete_code"


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
    assert res_j["debug_key"] == "incomplete_code"


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
    assert res_j["debug_key"] == "incomplete_code"


mock_symm_key = {
    "id": 2,
    "algorithm": "symmetric",
    "public": None,
    "private": "8T3oEm_haJZbn6xu-klttJXk5QBPYlurQrqA5SDx-Ck",
    "public_format": None,
    "public_encoding": None,
    "private_format": "none",
    "private_encoding": "base64url",
}
mock_token_key = {
    "id": 1,
    "algorithm": "ed448",
    "public": (
        "-----BEGIN PUBLIC"
        " KEY-----\nMEMwBQYDK2VxAzoAtPGddEupA3b5P5yr9gT3rvjzWeQH5cedY6RcwN3A5zTS9n8C\nc6dOR+XUPVLVu0o0i/t46fW1HMQA\n-----END"
        " PUBLIC KEY-----\n"
    ),
    "private": (
        "-----BEGIN PRIVATE"
        " KEY-----\nMEcCAQAwBQYDK2VxBDsEOY1wa98ZvsK8pYML+ICD9Mbtavr+QC5PC301oVn5jPM6\nT8tECKaZvu5mxG/OfxlEKxl/XIKuClP1mw==\n-----END"
        " PRIVATE KEY-----\n"
    ),
    "public_format": "X509PKCS#1",
    "public_encoding": "PEM",
    "private_format": "PKCS#8",
    "private_encoding": "PEM",
}


@pytest.fixture
def mock_get_keys(mocker: MockerFixture):
    get_k_s = mocker.patch("auth.data.keys.get_symmetric_key")
    get_k_s.return_value = A256GCMKey(kid="b", symmetric=mock_symm_key["private"])
    get_k_p = mocker.patch("auth.data.keys.get_pem_private_key")
    get_k_p.return_value = PEMPrivateKey(
        kid="a", public=mock_token_key["public"], private=mock_token_key["private"]
    )


def cr_user_id(id_int: int, g_id_name: str):
    return f"{id_int}_{g_id_name}"


code_session_key = "somecomplexsessionkey"
mock_redirect = "http://localhost:3000/auth/callback"
mock_flow_id = "1d5c621ea3a2da319fe0d0a680046fd6369a60e450ff04f59c51b0bfb3d96eef"
fake_token_scope = "test"
mock_user_id_int = 20
mock_user_id_fn = "mr"
mock_user_id_ln = "lastmocker"
mock_user_email = "mr@mocker.nl"
mock_user_id_name = gen_id_name(mock_user_id_fn, mock_user_id_ln)
mock_user_id = cr_user_id(mock_user_id_int, mock_user_id_name)
mock_flow_user = FlowUser(
    auth_time=utc_timestamp() - 20,
    flow_id=mock_flow_id,
    scope=fake_token_scope,
    user_id=mock_user_id,
)
mock_userdata = UserData(
    user_id=mock_user_id,
    active=True,
    firstname="Test",
    lastname="Register",
    email=mock_user_email,
    phone="06",
    av40id=123,
    joined=date.today(),
    registered=False,
    showage=False,
)
mock_auth_request = AuthRequest(
    response_type="code",
    client_id="dodekaweb_client",
    redirect_uri=mock_redirect,
    state="KV6A2hTOv6mOFYVpTAOmWw",
    code_challenge="8LNMS54GS7iB7H67U5OFLclCl0F87vy5uf-Izj3TCdQ",
    code_challenge_method="S256",
    nonce="-eB2lpr1IqZdJzt9CfDZ5jrHGa6yE87UUTFd4CWweOI",
)
nonce_original = "6SWk9T1sUfqgSYeq2XlawA"
code_verifier = "NiiCPTK4e73kAVCfWZyZX6AvIXyPg396Q4063oGOI3w"

fake_token_id = 44


@pytest.fixture
def fake_tokens():
    from auth.token.build_util import encode_token_dict
    from auth.token.build import finish_tokens
    from auth.token.build import create_tokens

    utc_now = utc_timestamp()
    mock_id_info = ops.userdata.id_info_from_ud(mock_userdata)
    access_token_data, id_token_data, access_scope, refresh_save = create_tokens(
        mock_flow_user.user_id,
        fake_token_scope,
        mock_flow_user.auth_time,
        mock_auth_request.nonce,
        utc_now,
        mock_id_info,
        DEFINE.issuer,
        DEFINE.frontend_client_id,
        DEFINE.backend_client_id,
        refresh_exp,
    )

    acc_val = encode_token_dict(access_token_data.model_dump())
    id_val = encode_token_dict(id_token_data.model_dump())

    aesgcm = aes_from_symmetric(mock_symm_key["private"])
    signing_key = PEMPrivateKey(
        kid="a", public=mock_token_key["public"], private=mock_token_key["private"]
    )

    refresh_token, access_token, id_token = finish_tokens(
        fake_token_id,
        refresh_save,
        aesgcm,
        access_token_data,
        id_token_data,
        mock_id_info,
        utc_now,
        signing_key,
        access_exp,
        id_exp,
        nonce="",
    )
    yield {
        "refresh": refresh_token,
        "access": access_token,
        "id": id_token,
        "family_id": refresh_save.family_id,
        "iat": refresh_save.iat,
        "exp": refresh_save.exp,
        "nonce": refresh_save.nonce,
        "acc_val": acc_val,
        "id_val": id_val,
        "user_id": refresh_save.user_id,
    }


def test_refresh(test_client, mocker: MockerFixture, mock_get_keys, fake_tokens):
    get_r = mocker.patch("apiserver.data.refreshtoken.RefreshOps.get_refresh_by_id")
    get_refr = mocker.patch("apiserver.data.refreshtoken.RefreshOps.insert_refresh_row")

    def side_effect(f_conn, id_int):
        if id_int == fake_token_id:
            return SavedRefreshToken(
                family_id=fake_tokens["family_id"],
                access_value=fake_tokens["acc_val"],
                id_token_value=fake_tokens["id_val"],
                iat=fake_tokens["iat"],
                exp=fake_tokens["exp"],
                nonce=fake_tokens["nonce"],
                user_id=fake_tokens["user_id"],
            )

    get_r.side_effect = side_effect
    get_refr.return_value = 45

    req = {
        "client_id": DEFINE.frontend_client_id,
        "grant_type": "refresh_token",
        "refresh_token": fake_tokens["refresh"],
    }

    response = test_client.post("/oauth/token/", json=req)
    # res_j = response.json()
    # print(res_j)
    assert response.status_code == codes.OK


def test_auth_code(test_client, mocker: MockerFixture, mock_get_keys):
    get_flow = mocker.patch("auth.data.authentication.pop_flow_user")
    get_auth = mocker.patch("auth.data.authorize.get_auth_request")
    get_ud = mocker.patch(
        "apiserver.data.api.ud.userdata.UserDataOps.get_userdata_by_id"
    )
    r_save = mocker.patch(
        "apiserver.data.api.refreshtoken.RefreshOps.insert_refresh_row"
    )

    def flow_side_effect(f_dsrc, code):
        if code == code_session_key:
            return mock_flow_user

    get_flow.side_effect = flow_side_effect

    def auth_side_effect(f_dsrc, flow_id):
        if flow_id == mock_flow_user.flow_id:
            return mock_auth_request

    get_auth.side_effect = auth_side_effect

    def ud_side_effect(conn, u_id):
        if u_id == mock_flow_user.user_id:
            return mock_userdata

    get_ud.side_effect = ud_side_effect

    r_save.return_value = 44

    req = {
        "client_id": DEFINE.frontend_client_id,
        "grant_type": "authorization_code",
        "code": code_session_key,
        "redirect_uri": mock_redirect,
        "code_verifier": code_verifier,
    }

    response = test_client.post("/oauth/token/", json=req)
    # res_j = response.json()
    # print(res_j)
    assert response.status_code == codes.OK


mock_opq_setup = {
    "id": 0,
    "value": "pd32VP-D21oNgNId22WdbEiUn5vUeFNhgNReuAv2FQvT8kyBZu9gW2kBn8E60HgbAEHDT6KCy575MVIzgLJQ2daSp_2XpESlXFbsxftf6Bw0_RYzAOZ1YL2Dnrtq1MwOF4jzOi3gs3bHnS_odl9VpaXz4GjQTT7aol5CYB0yYgE",
}


@pytest.fixture
def store_fix():
    store = dict()
    yield store


@pytest.fixture
def state_store(store_fix, mocker: MockerFixture):
    s_store = mocker.patch("auth.data.authentication.store_auth_state")

    def store_side_effect(f_dsrc, auth_id, state):
        store_fix[auth_id] = state

    s_store.side_effect = store_side_effect

    yield store_fix


@pytest.fixture
def register_state_store(store_fix, mocker: MockerFixture):
    s_store = mocker.patch("auth.data.register.store_auth_register_state")

    def store_side_effect(f_dsrc, auth_id, state):
        store_fix[auth_id] = state

    s_store.side_effect = store_side_effect

    yield store_fix


@pytest.fixture
def flow_store(store_fix, mocker: MockerFixture):
    f_store = mocker.patch("auth.data.authentication.store_flow_user")

    def store_side_effect(f_dsrc, s_key, flow_user):
        store_fix[s_key] = flow_user

    f_store.side_effect = store_side_effect

    yield store_fix


def test_start_register(test_client, mocker: MockerFixture, register_state_store: dict):
    t_hash = mocker.patch("auth.modules.register.random_time_hash_hex")
    test_user_email = "start@loginer.nl"
    user_fn = "terst"
    user_ln = "nagmer"
    test_user_id_int = 92
    test_id_name = gen_id_name(user_fn, user_ln)
    test_user_id = cr_user_id(test_user_id_int, test_id_name)
    test_auth_id = "9a051d2a4860b9d48624be0206f0743d6ce2f0686cc4cc842d97ea4e51c0b181"

    def hash_side_effect(user_usph):
        if user_usph == test_user_id:
            return test_auth_id

    t_hash.side_effect = hash_side_effect

    g_ud = mocker.patch("apiserver.data.api.ud.userdata.get_userdata_by_register_id")
    test_register_id = (
        "8c01e95c6021f62f7fc7a0c6149df725129fa4ea846edc1cdc0b13905e880f0c"
    )

    def ud_side_effect(conn, register_id):
        if register_id == test_register_id:
            return UserData(
                user_id=test_user_id,
                active=True,
                firstname="Test",
                lastname="Register",
                email=test_user_email,
                phone="06",
                av40id=123,
                joined=date.today(),
                registered=False,
                showage=True,
            )

    g_ud.side_effect = ud_side_effect

    g_u = mocker.patch("apiserver.data.api.user.UserOps.get_user_by_id")

    def u_side_effect(conn, user_id):
        if user_id == test_user_id:
            return User(
                id=test_user_id_int,
                id_name=test_id_name,
                user_id=test_user_id,
                password_file="",
                email=test_user_email,
            )

    g_u.side_effect = u_side_effect

    opq_setup = mocker.patch("auth.data.authentication.get_apake_setup")
    opq_setup.return_value = mock_opq_setup["value"]

    # password 'clientele'
    req = {
        "email": test_user_email,
        "client_request": "GM3pwtpnoj4e9JQJtectg6lZ7FYRZmD6fGo4cMttmSc",
        "register_id": test_register_id,
    }

    response = test_client.post("/onboard/register/", json=req)
    res_j = response.json()
    print(res_j)
    # example state
    # n-aQ8YSkFMbIoTJPS46lBeO4X4v5KbQ52ztB9-xP8wg
    # example message
    # GGnMPMzUGlKDTd0O4Yjw2S3sNrte4a1ybatXCr_-cRvyxVgYqutFLW3oUC5bmAczDl2DMzPRvmukMc-eKmSsZg
    assert res_j["auth_id"] == test_auth_id
    assert response.status_code == codes.OK
    saved_state = SavedRegisterState.model_validate(register_state_store[test_auth_id])
    assert saved_state.user_id == test_user_id


def test_finish_register(test_client, mocker: MockerFixture):
    test_auth_id = "e5a289429121408d95d7e3cde62d0f06da22b86bd49c2a34233423ed4b5e877e"
    test_user_email = "start@loginer.nl"
    user_fn = "terst"
    user_ln = "nagmer"
    test_user_id_int = 92
    test_id_name = gen_id_name(user_fn, user_ln)
    test_user_id = cr_user_id(test_user_id_int, test_id_name)
    test_r_id = "5488f0d6b6534a15"

    # password 'clientele'
    # test_state = "n-aQ8YSkFMbIoTJPS46lBeO4X4v5KbQ52ztB9-xP8wg"

    g_state = mocker.patch("apiserver.data.trs.reg.get_register_state")
    g_ud_rid = mocker.patch(
        "apiserver.data.api.ud.userdata.get_userdata_by_register_id"
    )

    def state_side_effect(f_dsrc, auth_id):
        if auth_id == test_auth_id:
            return SavedRegisterState(user_id=test_user_id)

    def ud_side_effect(conn, r_id):
        if r_id == test_r_id:
            return UserData(
                user_id=test_user_id,
                email=test_user_email,
                active=False,
                firstname="first",
                lastname="last",
                phone="063",
                av40id=2,
                joined=date.today(),
                registered=False,
                showage=True,
            )

    g_state.side_effect = state_side_effect
    g_ud_rid.side_effect = ud_side_effect

    # password 'clientele'
    req = {
        "email": test_user_email,
        "client_request": "iGq1MWDlVlZo_LG4o28Si9xV-Qt0IxKZ4NcLhhR470W9Wn_-9F4gCjfFD1GsPGayGF1oJ2FzyZXLzUS-MmaHO2pTGoD_QyGBiIV9s7LBYxFM_fciaaI08ZahLfj4kmXJVnOleHfXPsTJ8aDkPdJJwVox_1GvDJ2owTGez1xdA-N5POX6W32CNPA15RASrcdZSt4bik_EyPLb8VmeDKG6_ofcxpLhDETau2nYujPKPoG29f8RY3E8yYVuHewVlYr0",
        "auth_id": test_auth_id,
        "register_id": test_r_id,
        "callname": "somecaller",
        "eduinstitution": "testinstitution",
        "birthdate": "2022-09-05",
        "age_privacy": True,
    }

    # TODO check saved data

    response = test_client.post("/onboard/finish/", json=req)
    # res_j = response.json()
    # print(res_j)
    # example password file
    # DnuCs40tbbcosYBGDyyMrrxNcq-wkzrjZTa65_pJ_QWONK6yr3F4DOLphiBzfmBcTO_icmKmbQps-iBcMiF5CQGnS6qC60tEmF-ffv9Thofssx_y5dixQrch3rCHg_9kMloGndIfuv7n8Sxu8toQD74KIBeOYQfuefdKXy6FGRbvUm4A06OVvkDFtNpkbLNIFkRh2h-m6ZDtMwhXLvBBClz77Jo_jzEYobRL3d-f7QrEiZhpehFlN0n5OecMiPFC-g
    # n-aQ8YSkFMbIoTJPS46lBeO4X4v5KbQ52ztB9-xP8wgeiTMc52ItDYFQshq4rfw5-WSoIqkg-H2BmoIFQbGBNwE_hacoe5llYjoExc93uFOc7OcGs8gqwbgJkWWp40rpC4IeS7WUzh-LwSn6fx2C5Vvx2m9T29U_bD0voDdEMROZi_rAJ1fc8nDvLtahFp91n6_YNkZH0P8289wpUdwfTcpC50gPaWel_TRH8zgK2ZddqO21ZV13d6HjRenRhbjWfw
    assert response.status_code == codes.OK


@pytest.fixture
def req_store(store_fix, mocker: MockerFixture):
    r_store = mocker.patch("auth.data.authorize.store_auth_request")

    def store_side_effect(f_store, req):
        store_fix[mock_flow_id] = req
        return mock_flow_id

    r_store.side_effect = store_side_effect

    yield store_fix