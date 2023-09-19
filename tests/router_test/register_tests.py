from contextlib import asynccontextmanager

import pytest
import tomli
from faker import Faker
from fastapi import FastAPI
from httpx import codes
from pytest_mock import MockerFixture
from sqlalchemy.ext.asyncio import AsyncConnection
from starlette.testclient import TestClient

from apiserver.app_def import create_app
from apiserver.app_lifespan import State, safe_startup, define_code
from apiserver.data import Source
from apiserver.data.frame import Code, RegisterFrame
from apiserver.env import load_config
from apiserver.lib.model.entities import UserData, User
from auth.core.model import (
    FlowUser,
)
from auth.core.util import utc_timestamp
from router_test.test_util import (
    make_test_user,
    GenUser,
    make_extended_test_user,
    OpaqueValues,
)
from test_resources import res_path


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
    cd = define_code()
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
        test_values_dict = tomli.load(f)

    yield test_values_dict


@pytest.fixture(scope="module")
def opq_val(test_values: dict):
    yield OpaqueValues.model_validate(test_values["opaque"])


def mock_register_start_frame(
    test_ud: UserData, test_user: User, test_register_id: str
):
    class MockRegisterFrame(RegisterFrame):
        @classmethod
        async def get_registration(
            cls, dsrc: Source, register_id: str
        ) -> tuple[UserData, User]:
            if test_register_id == register_id:
                return test_ud, test_user

    return MockRegisterFrame


def test_start_register(test_client, gen_ext_user, make_cd: Code):
    test_user, test_user_info = gen_ext_user
    # t_hash = mocker.patch("auth.modules.register.random_time_hash_hex")
    # test_user_email = "start@loginer.nl"
    # user_fn = "terst"
    # user_ln = "nagmer"
    # test_user_id_int = 92
    # test_id_name = gen_id_name(user_fn, user_ln)
    # test_user_id = cr_user_id(test_user_id_int, test_id_name)
    test_auth_id = "9a051d2a4860b9d48624be0206f0743d6ce2f0686cc4cc842d97ea4e51c0b181"

    make_cd.frame.register_frm = mock_register_start_frame()

    t_hash.side_effect = hash_side_effect

    g_ud = mocker.patch("apiserver.data.api.ud.userdata.get_userdata_by_register_id")
    test_register_id = (
        "8c01e95c6021f62f7fc7a0c6149df725129fa4ea846edc1cdc0b13905e880f0c"
    )

    def ud_side_effect(conn, register_id):
        if register_id == test_register_id:
            return

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
