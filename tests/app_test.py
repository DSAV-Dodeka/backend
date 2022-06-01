from urllib.parse import urlparse, parse_qs

import asyncio

import pytest
import pytest_asyncio
from pytest_mock import MockerFixture

from httpx import AsyncClient
from fastapi import status

import opaquepy as opq

from dodekaserver.define import FlowUser, AuthRequest, SavedState
from dodekaserver.env import frontend_client_id
from dodekaserver.utilities import utc_timestamp, usp_hex
from dodekaserver.define.entities import SavedRefreshToken
from dodekaserver.db.ops import DbOperations


@pytest.fixture(scope="module")
def event_loop():
    """ Necessary for async tests with module-scoped fixtures """
    loop = asyncio.get_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="module")
async def app_mod():
    import dodekaserver.app as app_mod

    yield app_mod


@pytest_asyncio.fixture(scope="module")
async def app(app_mod):
    # startup, shutdown is not run
    app = app_mod.app
    yield app


@pytest_asyncio.fixture(scope="module", autouse=True)
async def mock_dsrc(app_mod, module_mocker: MockerFixture):
    app_mod.dsrc.gateway = module_mocker.MagicMock(spec=app_mod.dsrc.gateway)
    app_mod.dsrc.gateway.ops = module_mocker.MagicMock(spec=DbOperations)
    yield app_mod.dsrc


@pytest_asyncio.fixture(scope="module")
async def test_client(app):
    async with AsyncClient(app=app, base_url="http://test") as test_client:
        yield test_client


@pytest.mark.asyncio
async def test_root(test_client):
    response = await test_client.get("/")

    assert response.status_code == 200
    assert response.json() == {"Hallo": "Atleten"}


@pytest.mark.asyncio
async def test_incorrect_client_id(test_client: AsyncClient):
    req = {
      "client_id": "incorrect",
      "grant_type": "",
      "code": "",
      "redirect_uri": "",
      "code_verifier": "",
      "refresh_token": ""
    }
    response = await test_client.post("/oauth/token/", json=req)
    assert response.status_code == 400
    assert response.json()["error"] == "invalid_client"


@pytest.mark.asyncio
async def test_incorrect_grant_type(test_client: AsyncClient):
    req = {
      "client_id": frontend_client_id,
      "grant_type": "wrong",
      "code": "",
      "redirect_uri": "",
      "code_verifier": "",
      "refresh_token": ""
    }

    response = await test_client.post("/oauth/token/", json=req)
    assert response.status_code == 400
    res_j = response.json()
    assert res_j["error"] == "unsupported_grant_type"


@pytest.mark.asyncio
async def test_empty_verifier(test_client: AsyncClient):
    req = {
        "client_id": frontend_client_id,
        "grant_type": "authorization_code",
        "code": "some",
        "redirect_uri": "some",
        "code_verifier": "",
        "refresh_token": ""
    }

    response = await test_client.post("/oauth/token/", json=req)
    assert response.status_code == 400
    res_j = response.json()
    assert res_j["error"] == "invalid_request"
    assert res_j["debug_key"] == "incomplete_code"


@pytest.mark.asyncio
async def test_missing_redirect(test_client: AsyncClient):
    req = {
        "client_id": frontend_client_id,
        "grant_type": "authorization_code",
        "code": "some",
        "code_verifier": "some",
        "refresh_token": ""
    }

    response = await test_client.post("/oauth/token/", json=req)
    assert response.status_code == 400
    res_j = response.json()
    assert res_j["error"] == "invalid_request"
    assert res_j["debug_key"] == "incomplete_code"


@pytest.mark.asyncio
async def test_empty_code(test_client: AsyncClient):
    req = {
        "client_id": frontend_client_id,
        "grant_type": "authorization_code",
        "code": "",
        "redirect_uri": "some",
        "code_verifier": "some",
        "refresh_token": ""
    }

    response = await test_client.post("/oauth/token/", json=req)
    assert response.status_code == 400
    res_j = response.json()
    assert res_j["error"] == "invalid_request"
    assert res_j["debug_key"] == "incomplete_code"


mock_symm_key = {
        'id': 2, 'algorithm': 'symmetric', 'public': None, 'private': '8T3oEm_haJZbn6xu-klttJXk5QBPYlurQrqA5SDx-Ck',
        'public_format': None, 'public_encoding': None, 'private_format': 'none', 'private_encoding': 'base64url'
    }
mock_token_key = {
    'id': 1, 'algorithm': 'ed448',
    'public': '-----BEGIN PUBLIC KEY-----\nMEMwBQYDK2VxAzoAtPGddEupA3b5P5yr9gT3rvjzWeQH5cedY6RcwN3A5zTS9n8C\nc6dOR+'
              'XUPVLVu0o0i/t46fW1HMQA\n-----END PUBLIC KEY-----\n',
    'private': '-----BEGIN PRIVATE KEY-----\nMEcCAQAwBQYDK2VxBDsEOY1wa98ZvsK8pYML+ICD9Mbtavr+QC5PC301oVn5jPM6\nT8tE'
               'CKaZvu5mxG/OfxlEKxl/XIKuClP1mw==\n-----END PRIVATE KEY-----\n',
    'public_format': 'X509PKCS#1', 'public_encoding': 'PEM', 'private_format': 'PKCS#8', 'private_encoding': 'PEM'
}


@pytest_asyncio.fixture
async def mock_get_keys(mocker: MockerFixture):
    get_k_s = mocker.patch('dodekaserver.data.key.get_refresh_symmetric')
    get_k_s.return_value = mock_symm_key['private']
    get_k_p = mocker.patch('dodekaserver.data.key.get_token_private')
    get_k_p.return_value = mock_token_key['private']


session_key = "somecomplexsessionkey"
mock_redirect = "http://localhost:3000/auth/callback"
mock_flow_id = "1d5c621ea3a2da319fe0d0a680046fd6369a60e450ff04f59c51b0bfb3d96eef"
mock_flow_user = FlowUser(user_usph="mrmock", auth_time=utc_timestamp()-20, flow_id=mock_flow_id)
mock_auth_request = AuthRequest(response_type="code", client_id="dodekaweb_client",
                                redirect_uri=mock_redirect,
                                state="KV6A2hTOv6mOFYVpTAOmWw",
                                code_challenge="8LNMS54GS7iB7H67U5OFLclCl0F87vy5uf-Izj3TCdQ",
                                code_challenge_method="S256",
                                nonce="-eB2lpr1IqZdJzt9CfDZ5jrHGa6yE87UUTFd4CWweOI")
nonce_original = "6SWk9T1sUfqgSYeq2XlawA"
code_verifier = "NiiCPTK4e73kAVCfWZyZX6AvIXyPg396Q4063oGOI3w"
fake_token_scope = "test"
fake_token_id = 44


@pytest_asyncio.fixture
async def fake_tokens():
    from dodekaserver.auth.tokens import create_tokens, aes_from_symmetric, finish_tokens, encode_token_dict
    utc_now = utc_timestamp()
    access_token_data, id_token_data, access_scope, refresh_save = \
        create_tokens(mock_flow_user.user_usph, fake_token_scope, mock_flow_user.auth_time, mock_auth_request.nonce, utc_now)

    acc_val = encode_token_dict(access_token_data.dict())
    id_val = encode_token_dict(id_token_data.dict())

    aesgcm = aes_from_symmetric(mock_symm_key['private'])
    signing_key = mock_token_key['private']

    refresh_token, access_token, id_token = finish_tokens(fake_token_id, refresh_save, aesgcm, access_token_data,
                                                          id_token_data, utc_now, signing_key, nonce="")
    yield {'refresh': refresh_token, 'access': access_token, 'id': id_token, 'family_id': refresh_save.family_id,
           'iat': refresh_save.iat, 'exp': refresh_save.exp, 'nonce': refresh_save.nonce, 'acc_val': acc_val,
           'id_val': id_val}


@pytest.mark.asyncio
async def test_refresh(test_client, mocker: MockerFixture, mock_get_keys, fake_tokens):

    get_r = mocker.patch('dodekaserver.data.refreshtoken.get_refresh_by_id')
    get_refr = mocker.patch('dodekaserver.data.refreshtoken.refresh_transaction')

    def side_effect(f_dsrc, id_int):
        if id_int == fake_token_id:
            return SavedRefreshToken(family_id=fake_tokens['family_id'], access_value=fake_tokens['acc_val'],
                                     id_token_value=fake_tokens['id_val'], iat=fake_tokens['iat'], exp=fake_tokens['exp'],
                                     nonce=fake_tokens['nonce'])
    get_r.side_effect = side_effect
    get_refr.return_value = 45

    req = {
        "client_id": frontend_client_id,
        "grant_type": "refresh_token",
        "refresh_token": fake_tokens['refresh'],
    }

    response = await test_client.post("/oauth/token/", json=req)
    # res_j = response.json()
    # print(res_j)
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_auth_code(test_client, mocker: MockerFixture, mock_get_keys):
    get_flow = mocker.patch('dodekaserver.data.kv.get_flow_user')
    get_auth = mocker.patch('dodekaserver.data.kv.get_auth_request')
    r_save = mocker.patch('dodekaserver.data.refreshtoken.refresh_save')

    def flow_side_effect(f_dsrc, code):
        if code == session_key:
            return mock_flow_user

    get_flow.side_effect = flow_side_effect

    def auth_side_effect(f_dsrc, flow_id):
        if flow_id == mock_flow_user.flow_id:
            return mock_auth_request

    get_auth.side_effect = auth_side_effect

    r_save.return_value = 44

    req = {
        "client_id": frontend_client_id,
        "grant_type": "authorization_code",
        "code": session_key,
        "redirect_uri": mock_redirect,
        "code_verifier": code_verifier
    }

    response = await test_client.post("/oauth/token/", json=req)
    # res_j = response.json()
    # print(res_j)
    assert response.status_code == 200


mock_opq_key = {
    'id': 0,
    'algorithm': 'curve25519ristretto',
    'public': '8sVYGKrrRS1t6FAuW5gHMw5dgzMz0b5rpDHPnipkrGY',
    'private': 'ueKnTS9wtXyPb44JER4CJBc6AzIN1Wi2kDXupR6TrQk',
    'public_format': 'none',
    'public_encoding': 'base64url',
    'private_format': 'none',
    'private_encoding': 'base64url'
}


@pytest_asyncio.fixture
async def store_fix():
    store = dict()
    yield store


@pytest_asyncio.fixture
async def state_store(store_fix, mocker: MockerFixture):
    s_store = mocker.patch('dodekaserver.data.kv.store_auth_state')

    def store_side_effect(f_dsrc, auth_id, state):
        store_fix[auth_id] = state

    s_store.side_effect = store_side_effect

    yield store_fix


@pytest_asyncio.fixture
async def flow_store(store_fix, mocker: MockerFixture):
    f_store = mocker.patch('dodekaserver.data.kv.store_flow_user')

    def store_side_effect(f_dsrc, s_key, flow_user):
        store_fix[s_key] = flow_user

    f_store.side_effect = store_side_effect

    yield store_fix


@pytest.mark.asyncio
async def test_start_register(test_client, mocker: MockerFixture, state_store: dict):
    test_username = "startregister"
    test_user_usph = usp_hex(test_username)
    test_auth_id = "9a051d2a4860b9d48624be0206f0743d6ce2f0686cc4cc842d97ea4e51c0b181"

    opq_key = mocker.patch('dodekaserver.data.key.get_opaque_public')
    opq_key.return_value = mock_opq_key['public']
    t_hash = mocker.patch('dodekaserver.utilities.random_time_hash_hex')
    r_opq = mocker.patch('dodekaserver.auth.authentication.opaque_register')

    def hash_side_effect(user_usph):
        if user_usph == test_user_usph:
            return test_auth_id
    t_hash.side_effect = hash_side_effect

    def opq_side_effect(request, user_usph, key):
        opq_response, state = opq.register(request, key)
        state_store['state'] = state
        state_store['opq_response'] = opq_response
        return opq_response, SavedState(user_usph=user_usph, state=state)
    r_opq.side_effect = opq_side_effect

    # password 'clientele'
    req = {
        "username": test_username,
        "client_request": "1nE62MQOsSCan3raiuU8UKuPkmCv41rxb41QrVY6ZFk",
    }

    response = await test_client.post("/register/start/", json=req)
    res_j = response.json()
    # print(res_j)
    # example state
    # n-aQ8YSkFMbIoTJPS46lBeO4X4v5KbQ52ztB9-xP8wg
    # example message
    # GGnMPMzUGlKDTd0O4Yjw2S3sNrte4a1ybatXCr_-cRvyxVgYqutFLW3oUC5bmAczDl2DMzPRvmukMc-eKmSsZg
    assert res_j['auth_id'] == test_auth_id
    assert res_j['server_message'] == state_store['opq_response']
    assert response.status_code == 200
    saved_state = SavedState.parse_obj(state_store[test_auth_id])
    assert saved_state.user_usph == test_user_usph
    assert saved_state.state == state_store['state']


@pytest.mark.asyncio
async def test_finish_register(test_client, mocker: MockerFixture):
    test_auth_id = "e5a289429121408d95d7e3cde62d0f06da22b86bd49c2a34233423ed4b5e877e"
    test_user = "atestperson"

    # password 'clientele' with mock_opq_key
    test_state = "n-aQ8YSkFMbIoTJPS46lBeO4X4v5KbQ52ztB9-xP8wg"
    test_user_usph = usp_hex(test_user)

    g_state = mocker.patch('dodekaserver.data.kv.get_state')

    def state_side_effect(f_dsrc, auth_id):
        if auth_id == test_auth_id:
            return SavedState(user_usph=test_user_usph, state=test_state)

    g_state.side_effect = state_side_effect

    # password 'clientele'
    req = {
        "username": test_user,
        "client_request": "HokzHOdiLQ2BULIauK38OflkqCKpIPh9gZqCBUGxgTcBP4WnKHuZZWI6BMXPd7hTnOznBrPIKsG4CZFlqeNK6QuCHku1lM4fi8Ep-n8dguVb8dpvU9vVP2w9L6A3RDETmYv6wCdX3PJw7y7WoRafdZ-v2DZGR9D_NvPcKVHcH03KQudID2lnpf00R_M4CtmXXajttWVdd3eh40Xp0YW41n8",
        "auth_id": test_auth_id
    }

    response = await test_client.post("/register/finish/", json=req)
    # res_j = response.json()
    # print(res_j)
    # example password file
    # DnuCs40tbbcosYBGDyyMrrxNcq-wkzrjZTa65_pJ_QWONK6yr3F4DOLphiBzfmBcTO_icmKmbQps-iBcMiF5CQGnS6qC60tEmF-ffv9Thofssx_y5dixQrch3rCHg_9kMloGndIfuv7n8Sxu8toQD74KIBeOYQfuefdKXy6FGRbvUm4A06OVvkDFtNpkbLNIFkRh2h-m6ZDtMwhXLvBBClz77Jo_jzEYobRL3d-f7QrEiZhpehFlN0n5OecMiPFC-g
    # n-aQ8YSkFMbIoTJPS46lBeO4X4v5KbQ52ztB9-xP8wgeiTMc52ItDYFQshq4rfw5-WSoIqkg-H2BmoIFQbGBNwE_hacoe5llYjoExc93uFOc7OcGs8gqwbgJkWWp40rpC4IeS7WUzh-LwSn6fx2C5Vvx2m9T29U_bD0voDdEMROZi_rAJ1fc8nDvLtahFp91n6_YNkZH0P8289wpUdwfTcpC50gPaWel_TRH8zgK2ZddqO21ZV13d6HjRenRhbjWfw
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_start_login(test_client, mocker: MockerFixture, state_store):
    test_user = "startloginer"

    opq_key = mocker.patch('dodekaserver.data.key.get_opaque_private')
    opq_key.return_value = mock_opq_key['private']

    g_pw = mocker.patch('dodekaserver.data.user.get_user_password_file')

    test_user_usph = usp_hex(test_user)

    fake_password_file = "n-aQ8YSkFMbIoTJPS46lBeO4X4v5KbQ52ztB9-xP8wgeiTMc52ItDYFQshq4rfw5-WSoIqkg-H2BmoIFQbGBNwE_hacoe5llYjoExc93uFOc7OcGs8gqwbgJkWWp40rpC4IeS7WUzh-LwSn6fx2C5Vvx2m9T29U_bD0voDdEMROZi_rAJ1fc8nDvLtahFp91n6_YNkZH0P8289wpUdwfTcpC50gPaWel_TRH8zgK2ZddqO21ZV13d6HjRenRhbjWfw"

    def pw_side_effect(f_dsrc, user_usph):
        if user_usph == test_user_usph:
            return fake_password_file

    g_pw.side_effect = pw_side_effect

    # password 'clientele'
    req = {
        "username": test_user,
        "client_request": "IBLgmoQ-rRjs9otxi8niNKXwEPnvqjfONz8IA6LzIjnwGqkLclrQy7fGi1doawiamM7ftIZaihkhNVKHeIx4IAAAxEhDt_NBTRwKsZNQ0noZfr5_tbI3ZzZfjf5L-yxv-38",
    }

    response = await test_client.post("/login/start/", json=req)
    res_j = response.json()
    print(res_j)
    # example state
    # WwX2il7d7yrV5ni0dkXFgLC4FCzIVJnFdg2zTGRgW8XGTTmS-O7usDTweIenOSNZRfs2D4r0eN1bV977GDWCS6kfVhgEwslqlaUbExXvFBlvEN1JY1ICYo5u5qDIVYaMscQiuf8oNNRHANPZ_l6gtdkBN6eTQ7SWY6F4Iy0gE3LPJKPBrkKl10zNLJ2oo69dkdCu1Er5UPzdo48wAH_WARXFKxwHLCZLxfFnN7eV6033CFdSJF9IR8Z6X177lcaB
    # example message
    # XE2e5baMjY3k342xZ5PgC9pyxOkFdSVlR_0EzzT-k2zyxVgYqutFLW3oUC5bmAczDl2DMzPRvmukMc-eKmSsZgE_hacoe5llYjoExc93uFOc7OcGs8gqwbgJkWWp40rpC4IeS7WUzh-LwSn6fx2C5Vvx2m9T29U_bD0voDdEMROZi_rAJ1fc8nDvLtahFp91n6_YNkZH0P8289wpUdwfTcpC50gPaWel_TRH8zgK2ZddqO21ZV13d6HjRenRhbjWf16FzOJAzS7mEtX0xyNJvjcA4r-MpHt7sA6PXHgZNZhzkHaurq_ZutvRWCWLzGHPjGs5t_nBf4oqIuL_hfQjT0wAAOZYJP4U2mUe3oT-3LXInys1LjAYGX1jvow53a-pJex6jcHOFPwEvOhn3CKXGrHL913o84s07IQNJ0TZ26zzC9M
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_finish_login(test_client, mocker: MockerFixture, flow_store):
    test_auth_id = "15dae3786b6d0f20629cf3a35187a8a9a3d038f2c31b7c55e658b35906f86e41"
    test_user = "finishloginer"

    # password 'clientele' with mock_opq_key
    test_state = "WwX2il7d7yrV5ni0dkXFgLC4FCzIVJnFdg2zTGRgW8XGTTmS-O7usDTweIenOSNZRfs2D4r0eN1bV977GDWCS6kfVhgEwslqlaUbExXvFBlvEN1JY1ICYo5u5qDIVYaMscQiuf8oNNRHANPZ_l6gtdkBN6eTQ7SWY6F4Iy0gE3LPJKPBrkKl10zNLJ2oo69dkdCu1Er5UPzdo48wAH_WARXFKxwHLCZLxfFnN7eV6033CFdSJF9IR8Z6X177lcaB"
    test_user_usph = usp_hex(test_user)

    g_state = mocker.patch('dodekaserver.data.kv.get_state')

    def state_side_effect(f_dsrc, auth_id):
        if auth_id == test_auth_id:
            return SavedState(user_usph=test_user_usph, state=test_state)

    g_state.side_effect = state_side_effect

    # password 'clientele'
    req = {
        "username": test_user,
        "client_request": "YATUKRGRBXjup27rb8TeoHFw8AlyZ1Kx5FB2oa4HLohCyU-BDaPLWm9CiRRCGHvp-PV9PThsLtjDLJXDEtnoXA",
        "auth_id": test_auth_id,
        "flow_id": "434586aeb15dcca4279446a0e386b863694d7bb75b6d48c63e408eae62eb297d"
    }

    response = await test_client.post("/login/finish/", json=req)
    res_j = response.json()
    print(res_j)
    # example session key
    # zySjwa5CpddMzSydqKOvXZHQrtRK-VD83aOPMAB_1gEVxSscBywmS8XxZze3letN9whXUiRfSEfGel9e-5XGgQ
    assert response.status_code == 200


@pytest_asyncio.fixture
async def req_store(store_fix, mocker: MockerFixture):
    r_store = mocker.patch('dodekaserver.data.kv.store_auth_request')

    def store_side_effect(f_dsrc, flow_id, req):
        store_fix[flow_id] = req

    r_store.side_effect = store_side_effect

    yield store_fix


@pytest.mark.asyncio
async def test_oauth_authorize(test_client: AsyncClient, req_store):
    req = {
        "response_type": "code",
        "client_id": "dodekaweb_client",
        "redirect_uri": "https://dsavdodeka.nl/auth/callback",
        "state": "KV6A2hTOv6mOFYVpTAOmWw",
        "code_challenge": "8LNMS54GS7iB7H67U5OFLclCl0F87vy5uf-Izj3TCdQ",
        "code_challenge_method": "S256",
        "nonce": "eB2lpr1IqZdJzt9CfDZ5jrHGa6yE87UUTFd4CWweOI"
    }

    response = await test_client.get("/oauth/authorize/", params=req)

    assert response.status_code == status.HTTP_303_SEE_OTHER


@pytest.mark.asyncio
async def test_oauth_callback(test_client: AsyncClient, mocker: MockerFixture):
    test_flow_id = "1cd7afeca7eb420201ea69e06d9085ae2b8dd84adaae8d27c89746aab75d1dff"
    test_code = "zySjwa5CpddMzSydqKOvXZHQrtRK-VD83aOPMAB_1gEVxSscBywmS8XxZze3letN9whXUiRfSEfGel9e-5XGgQ"

    get_auth = mocker.patch('dodekaserver.data.kv.get_auth_request')

    def auth_side_effect(f_dsrc, flow_id):
        if flow_id == test_flow_id:
            return mock_auth_request

    get_auth.side_effect = auth_side_effect

    req = {
        "flow_id": test_flow_id,
        "code": test_code,
    }

    response = await test_client.get("/oauth/callback/", params=req)
    loc = response.headers['location']
    queries = parse_qs(urlparse(loc).query)
    print(response)
    assert queries['code'] == [test_code]
    assert queries['state'] == [mock_auth_request.state]
    assert response.status_code == status.HTTP_303_SEE_OTHER
