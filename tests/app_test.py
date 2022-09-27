from datetime import date
from pathlib import Path
from urllib.parse import urlparse, parse_qs

import asyncio

import pytest
import pytest_asyncio
from pytest_mock import MockerFixture

from httpx import AsyncClient
from fastapi import status

from apiserver.auth.tokens import id_info_from_ud
from apiserver.data.user import gen_id_name
from apiserver.define import FlowUser, AuthRequest, SavedState, SavedRegisterState, frontend_client_id
from apiserver.env import load_config
from apiserver.utilities import utc_timestamp, usp_hex
from apiserver.define.entities import SavedRefreshToken, UserData, User
from apiserver.db.ops import DbOperations


@pytest.fixture(scope="module")
def event_loop():
    """ Necessary for async tests with module-scoped fixtures """
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="module")
async def app_mod():
    import apiserver.app as app_mod

    yield app_mod


@pytest_asyncio.fixture(scope="module")
async def app(app_mod):
    # startup, shutdown is not run
    app = app_mod.app
    yield app


@pytest.fixture(scope="module")
def api_config():
    test_config_path = Path(__file__).parent.joinpath("testenv.toml")
    yield load_config(test_config_path)


@pytest_asyncio.fixture(scope="module", autouse=True)
async def mock_dsrc(app_mod, app, api_config, module_mocker: MockerFixture):
    app.state.dsrc.gateway = module_mocker.MagicMock(spec=app.state.dsrc.gateway)
    app.state.dsrc.gateway.ops = module_mocker.MagicMock(spec=DbOperations)
    app_mod.safe_startup(app, app.state.dsrc, api_config)
    yield app.state.dsrc


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
    get_k_s = mocker.patch('apiserver.data.key.get_refresh_symmetric')
    get_k_s.return_value = mock_symm_key['private']
    get_k_p = mocker.patch('apiserver.data.key.get_token_private')
    get_k_p.return_value = mock_token_key['private']


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
mock_flow_user = FlowUser(auth_time=utc_timestamp() - 20, flow_id=mock_flow_id,
                          scope=fake_token_scope, user_id=mock_user_id)
mock_userdata = UserData(user_id=mock_user_id, active=True, firstname="Test", lastname="Register",
                              email=mock_user_email, phone="06", av40id=123, joined=date.today(), registered=False)
mock_auth_request = AuthRequest(response_type="code", client_id="dodekaweb_client",
                                redirect_uri=mock_redirect,
                                state="KV6A2hTOv6mOFYVpTAOmWw",
                                code_challenge="8LNMS54GS7iB7H67U5OFLclCl0F87vy5uf-Izj3TCdQ",
                                code_challenge_method="S256",
                                nonce="-eB2lpr1IqZdJzt9CfDZ5jrHGa6yE87UUTFd4CWweOI")
nonce_original = "6SWk9T1sUfqgSYeq2XlawA"
code_verifier = "NiiCPTK4e73kAVCfWZyZX6AvIXyPg396Q4063oGOI3w"

fake_token_id = 44


@pytest_asyncio.fixture
async def fake_tokens():
    from apiserver.auth.tokens import create_tokens, aes_from_symmetric, finish_tokens, encode_token_dict
    utc_now = utc_timestamp()
    mock_id_info = id_info_from_ud(mock_userdata)
    access_token_data, id_token_data, access_scope, refresh_save = \
        create_tokens(mock_flow_user.user_id, fake_token_scope, mock_flow_user.auth_time,
                      mock_auth_request.nonce, utc_now, mock_id_info)

    acc_val = encode_token_dict(access_token_data.dict())
    id_val = encode_token_dict(id_token_data.dict())

    aesgcm = aes_from_symmetric(mock_symm_key['private'])
    signing_key = mock_token_key['private']

    refresh_token, access_token, id_token = finish_tokens(fake_token_id, refresh_save, aesgcm, access_token_data,
                                                          id_token_data, utc_now, signing_key, nonce="")
    yield {'refresh': refresh_token, 'access': access_token, 'id': id_token, 'family_id': refresh_save.family_id,
           'iat': refresh_save.iat, 'exp': refresh_save.exp, 'nonce': refresh_save.nonce, 'acc_val': acc_val,
           'id_val': id_val, 'user_id': refresh_save.user_id}


@pytest.mark.asyncio
async def test_refresh(test_client, mocker: MockerFixture, mock_get_keys, fake_tokens):
    get_r = mocker.patch('apiserver.data.refreshtoken.get_refresh_by_id')
    get_refr = mocker.patch('apiserver.data.refreshtoken.insert_refresh_row')

    def side_effect(f_dsrc, conn, id_int):
        if id_int == fake_token_id:
            return SavedRefreshToken(family_id=fake_tokens['family_id'], access_value=fake_tokens['acc_val'],
                                     id_token_value=fake_tokens['id_val'], iat=fake_tokens['iat'],
                                     exp=fake_tokens['exp'],
                                     nonce=fake_tokens['nonce'], user_id=fake_tokens['user_id'])

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
    get_flow = mocker.patch('apiserver.data.kv.pop_flow_user')
    get_auth = mocker.patch('apiserver.data.kv.get_auth_request')
    get_ud = mocker.patch('apiserver.data.user.get_userdata_by_id')
    r_save = mocker.patch('apiserver.data.refreshtoken.insert_refresh_row')

    def flow_side_effect(f_dsrc, code):
        if code == code_session_key:
            return mock_flow_user

    get_flow.side_effect = flow_side_effect

    def auth_side_effect(f_dsrc, flow_id):
        if flow_id == mock_flow_user.flow_id:
            return mock_auth_request

    get_auth.side_effect = auth_side_effect

    def ud_side_effect(f_dsrc, conn, u_id):
        if u_id == mock_flow_user.user_id:
            return mock_userdata

    get_ud.side_effect = ud_side_effect

    r_save.return_value = 44

    req = {
        "client_id": frontend_client_id,
        "grant_type": "authorization_code",
        "code": code_session_key,
        "redirect_uri": mock_redirect,
        "code_verifier": code_verifier
    }

    response = await test_client.post("/oauth/token/", json=req)
    # res_j = response.json()
    # print(res_j)
    assert response.status_code == 200


mock_opq_setup = {
    'id': 0,
    'value': 'pd32VP-D21oNgNId22WdbEiUn5vUeFNhgNReuAv2FQvT8kyBZu9gW2kBn8E60HgbAEHDT6KCy575MVIzgLJQ2daSp_2XpESlXFbsxftf6Bw0_RYzAOZ1YL2Dnrtq1MwOF4jzOi3gs3bHnS_odl9VpaXz4GjQTT7aol5CYB0yYgE'
}


@pytest_asyncio.fixture
async def store_fix():
    store = dict()
    yield store


@pytest_asyncio.fixture
async def state_store(store_fix, mocker: MockerFixture):
    s_store = mocker.patch('apiserver.data.kv.store_auth_state')

    def store_side_effect(f_dsrc, auth_id, state):
        store_fix[auth_id] = state

    s_store.side_effect = store_side_effect

    yield store_fix


@pytest_asyncio.fixture
async def register_state_store(store_fix, mocker: MockerFixture):
    s_store = mocker.patch('apiserver.data.kv.store_auth_register_state')

    def store_side_effect(f_dsrc, auth_id, state):
        store_fix[auth_id] = state

    s_store.side_effect = store_side_effect

    yield store_fix


@pytest_asyncio.fixture
async def flow_store(store_fix, mocker: MockerFixture):
    f_store = mocker.patch('apiserver.data.kv.store_flow_user')

    def store_side_effect(f_dsrc, s_key, flow_user):
        store_fix[s_key] = flow_user

    f_store.side_effect = store_side_effect

    yield store_fix


@pytest.mark.asyncio
async def test_start_register(test_client, mocker: MockerFixture, register_state_store: dict):
    t_hash = mocker.patch('apiserver.utilities.random_time_hash_hex')
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

    g_ud = mocker.patch('apiserver.data.user.get_userdata_by_register_id')
    test_register_id = "8c01e95c6021f62f7fc7a0c6149df725129fa4ea846edc1cdc0b13905e880f0c"

    def ud_side_effect(f_dsrc, conn, register_id):
        if register_id == test_register_id:
            return UserData(user_id=test_user_id, active=True, firstname="Test", lastname="Register", email=test_user_email,
                            phone="06",
                            av40id=123, joined=date.today(), registered=False)

    g_ud.side_effect = ud_side_effect

    g_u = mocker.patch('apiserver.data.user.get_user_by_id')

    def u_side_effect(f_dsrc, conn, user_id):
        if user_id == test_user_id:
            return User(id=test_user_id_int, id_name=test_id_name, user_id=test_user_id, password_file="",
                        email=test_user_email)

    g_u.side_effect = u_side_effect

    opq_setup = mocker.patch('apiserver.data.opaquesetup.get_setup')
    opq_setup.return_value = mock_opq_setup['value']

    # password 'clientele'
    req = {
        "email": test_user_email,
        "client_request": "GM3pwtpnoj4e9JQJtectg6lZ7FYRZmD6fGo4cMttmSc",
        "register_id": test_register_id
    }

    response = await test_client.post("/onboard/register/", json=req)
    res_j = response.json()
    print(res_j)
    # example state
    # n-aQ8YSkFMbIoTJPS46lBeO4X4v5KbQ52ztB9-xP8wg
    # example message
    # GGnMPMzUGlKDTd0O4Yjw2S3sNrte4a1ybatXCr_-cRvyxVgYqutFLW3oUC5bmAczDl2DMzPRvmukMc-eKmSsZg
    assert res_j['auth_id'] == test_auth_id
    assert response.status_code == 200
    saved_state = SavedRegisterState.parse_obj(register_state_store[test_auth_id])
    assert saved_state.user_id == test_user_id


@pytest.mark.asyncio
async def test_finish_register(test_client, mocker: MockerFixture):
    test_auth_id = "e5a289429121408d95d7e3cde62d0f06da22b86bd49c2a34233423ed4b5e877e"
    test_user_email = "start@loginer.nl"
    user_fn = "terst"
    user_ln = "nagmer"
    test_user_id_int = 92
    test_id_name = gen_id_name(user_fn, user_ln)
    test_user_id = cr_user_id(test_user_id_int, test_id_name)
    test_r_id = "5488f0d6b6534a15"

    # password 'clientele'
    test_state = "n-aQ8YSkFMbIoTJPS46lBeO4X4v5KbQ52ztB9-xP8wg"

    g_state = mocker.patch('apiserver.data.kv.get_register_state')
    g_ud_rid = mocker.patch('apiserver.data.user.get_userdata_by_register_id')

    def state_side_effect(f_dsrc, auth_id):
        if auth_id == test_auth_id:
            return SavedRegisterState(user_id=test_user_id)

    def ud_side_effect(f_dsrc, conn, r_id):
        if r_id == test_r_id:
            return UserData(user_id=test_user_id, email=test_user_email, active=False, firstname="first", lastname="last", phone="063",
                            av40id=2, joined=date.today(), registered=False)

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
        "birthdate": "2022-09-05"
    }

    # TODO check saved data

    response = await test_client.post("/onboard/finish/", json=req)
    # res_j = response.json()
    # print(res_j)
    # example password file
    # DnuCs40tbbcosYBGDyyMrrxNcq-wkzrjZTa65_pJ_QWONK6yr3F4DOLphiBzfmBcTO_icmKmbQps-iBcMiF5CQGnS6qC60tEmF-ffv9Thofssx_y5dixQrch3rCHg_9kMloGndIfuv7n8Sxu8toQD74KIBeOYQfuefdKXy6FGRbvUm4A06OVvkDFtNpkbLNIFkRh2h-m6ZDtMwhXLvBBClz77Jo_jzEYobRL3d-f7QrEiZhpehFlN0n5OecMiPFC-g
    # n-aQ8YSkFMbIoTJPS46lBeO4X4v5KbQ52ztB9-xP8wgeiTMc52ItDYFQshq4rfw5-WSoIqkg-H2BmoIFQbGBNwE_hacoe5llYjoExc93uFOc7OcGs8gqwbgJkWWp40rpC4IeS7WUzh-LwSn6fx2C5Vvx2m9T29U_bD0voDdEMROZi_rAJ1fc8nDvLtahFp91n6_YNkZH0P8289wpUdwfTcpC50gPaWel_TRH8zgK2ZddqO21ZV13d6HjRenRhbjWfw
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_start_login(test_client, mocker: MockerFixture, state_store: dict):
    opq_setup = mocker.patch('apiserver.data.opaquesetup.get_setup')
    opq_setup.return_value = mock_opq_setup['value']

    g_pw = mocker.patch('apiserver.data.user.get_user_by_id')
    g_pw_email = mocker.patch('apiserver.data.user.get_user_by_email')
    test_user_email = "start@loginer.nl"
    user_fn = "test"
    user_ln = "namer"
    test_user_id_int = 99
    test_id_name = gen_id_name(user_fn, user_ln)
    test_user_id = cr_user_id(test_user_id_int, test_id_name)

    fake_password_file = "GLgWMaiuTTs2NyK9gvrhbtUMTrHLy2erbEwPnzwFDQ6i5EuUyWEN9yqEarTqxprZ205gkQoY_yks3-1jr3XuTfKfh1byl9LZHFpDA-FWNyc5wV5CBYz_jzruanzI-yFCPt7fPglNFs7mnwPbZaraoKMJX5prMMrULtDF4KlZuv2szqISaM3d9kiVUEgXzNAPh6EMuN1GCySL8gimFyfZxfrk3QCeQJKudx2YZYz9ReBs7EkmAwTCHxeiCmYaDdlu"
    correct_password_file = "6sr_nvpqPqB-GCjj091vbsIsKYdHX2BE_9ICHT-8o329Wn_-9F4gCjfFD1GsPGayGF1oJ2FzyZXLzUS-MmaHO2pTGoD_QyGBiIV9s7LBYxFM_fciaaI08ZahLfj4kmXJfzqcWVSecc7uqgzR5DVamDHlmQUOT6QjXcDmbuPm8eDu1hBdD65ZWmpUz16DK3-k6uBLjQ1fKYj8o3xBShhRQCKpm0PFCjk4uABkXgdzy5EWoKkTZ8cslYe450nAdOqv"

    def pw_side_effect(f_dsrc, f_conn, user_id):
        if user_id == "1_fakerecord":
            return User(id=1, id_name="fakerecord", password_file=fake_password_file, scope="none",
                        user_id="1_fakerecord", email="fakeemail")

    g_pw.side_effect = pw_side_effect

    def pw_em_side_effect(f_dsrc, f_conn, user_email):
        if user_email == test_user_email:
            return User(id=test_user_id_int, id_name=test_id_name, password_file=correct_password_file, scope="none",
                        user_id=test_user_id, email=test_user_email)

    g_pw_email.side_effect = pw_em_side_effect

    t_hash = mocker.patch('apiserver.utilities.random_time_hash_hex')
    test_auth_id = "d7a822c06ca8faa0e1df42fe3cbb0371"

    def hash_side_effect(user_usph):
        if user_usph == test_user_id:
            return test_auth_id

    t_hash.side_effect = hash_side_effect

    # password 'clientele'
    req = {
        "email": test_user_email,
        "client_request": "ht_LfPlozB5sa76eflmWeulgGU4dU4aeEutzyDMTkRoB3bO62RP95nc1PWt6IdJxpiuMW5OsoWEWNpa4EUZrxqAB8a5mLVLBQ81Y-30YlSgppQNdWAgeA-amu93cEisx",
    }

    response = await test_client.post("/login/start/", json=req)
    res_j = response.json()
    print(res_j)
    # example message
    # ALBAwXBHmhQd_ifiKP8NODRQ3mOWG6m8-zFmmJVdUn9Sot6VDE6Gv1G7nwmXDdZ35lyzYoKlqW2Z4czRkngvu53aA66H-Ir4r2qu_Im6qb9fQ0vYxFxq7Ecc1hi90RUztLu5OrI-BtWHzzsBSU5RvKl07JITisMv3o8ae87vxFl8z7nQEAXpy5-ZTqTh9EvKdIEHETSea0BBTHyUQ5mZA55c3mXsVKEKpk0zRcuzyr8CdX8a-1pwdDkG40ZTwE_AxAXORiNsicTq-ZspiDwSkag9Exp-_2H-g2sY3s_8k_YUBIXo7B2i9YOZe5ygA3eU8EQKusWjqJ0lJ1tObZdgPFOTTsryGFcRFLvLE-QH83tV91S5n3Rc9nChlSlAghwVjW5vH1hE9OrtzViSSFSd_oQxpl3t8JXXI6v15qWdYTA
    # example state
    # NxOxeb4oKwirncPlH1SlCbE_md8lH767HsgGv57G1l3aMinOwsi9BDWQW054L-iqZh9le2YqQ4LI10kCbfh4ijIV36HPrGDZg1ObZKx4U1Mgg-5wnLKZx-qtUukSWgON8a0fkN7_C_Jazl8oZxKC4fXBbJj1NKKn2xZM0yrezur9PbOOAi8m9g4WTgKcEwyHGXz41dey2QetWH2GnK-w540e3mdi5vP9q7NPGXOJ-I6TIqvU9tp5B3539LnwwTE1
    assert response.status_code == 200
    assert test_auth_id in state_store.keys()
    assert res_j['auth_id'] == test_auth_id
    print(state_store[test_auth_id])


@pytest.mark.asyncio
async def test_finish_login(test_client, mocker: MockerFixture, flow_store: dict):
    test_auth_id = "15dae3786b6d0f20629cf"
    user_fn = "test"
    user_ln = "namerf"
    test_user_id_int = 40
    gen_id_name(user_fn, user_ln)
    test_user_id = cr_user_id(test_user_id_int, gen_id_name)
    test_email = "finish@login.nl"

    # password 'clientele' with mock_opq_key
    g_state = mocker.patch('apiserver.data.kv.get_state')
    test_state = "NxOxeb4oKwirncPlH1SlCbE_md8lH767HsgGv57G1l3aMinOwsi9BDWQW054L-iqZh9le2YqQ4LI10kCbfh4ijIV36HPrGDZg1ObZKx4U1Mgg-5wnLKZx-qtUukSWgON8a0fkN7_C_Jazl8oZxKC4fXBbJj1NKKn2xZM0yrezur9PbOOAi8m9g4WTgKcEwyHGXz41dey2QetWH2GnK-w540e3mdi5vP9q7NPGXOJ-I6TIqvU9tp5B3539LnwwTE1"

    def state_side_effect(f_dsrc, auth_id):
        if auth_id == test_auth_id:
            return SavedState(user_id=test_user_id, state=test_state, scope=fake_token_scope, user_email=test_email)

    g_state.side_effect = state_side_effect

    flow_id = "df60854e55352c9ff02f768a888710c3"
    # password 'clientele'
    req = {
        "email": test_email,
        "client_request": "28gMIH7k8inGBdiMrpKidOtwtbcUlgMkmRNGVBy6CrXF_XPtVbzCwmtVCeUEuTSeRkyKFqDnD-v9AXcEfPUZ1w",
        "auth_id": test_auth_id,
        "flow_id": flow_id
    }
    session_key = "_T2zjgIvJvYOFk4CnBMMhxl8-NXXstkHrVh9hpyvsOeNHt5nYubz_auzTxlzifiOkyKr1PbaeQd-d_S58MExNQ"

    response = await test_client.post("/login/finish/", json=req)

    assert session_key in flow_store.keys()
    flow_user = FlowUser.parse_obj(flow_store[session_key])
    assert flow_user.flow_id == flow_id
    assert flow_user.scope == fake_token_scope
    assert response.status_code == 200


@pytest_asyncio.fixture
async def req_store(store_fix, mocker: MockerFixture):
    r_store = mocker.patch('apiserver.data.kv.store_auth_request')

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

    get_auth = mocker.patch('apiserver.data.kv.get_auth_request')

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
