import pytest
import tomllib
from faker import Faker
from httpx import codes
from apiserver.app.error import AppError, ErrorKeys

from apiserver.data import Source
from apiserver.data.context import Code, RegisterAppContext
from apiserver.lib.model.entities import UserData, User
from auth.core.model import (
    FlowUser,
    SavedRegisterState,
)
from auth.core.util import utc_timestamp
from auth.data.context import RegisterContext
from tests.test_util import (
    make_test_user,
    GenUser,
    OpaqueValues,
    make_base_ud,
)
from store import Store
from store.error import NoDataError
from tests.test_resources import res_path


@pytest.fixture
def gen_user(faker: Faker):
    yield make_test_user(faker)


@pytest.fixture
def gen_ud_u(faker: Faker):
    yield make_base_ud(faker)


pytest_plugins = [
    "tests.router_test.data_fixtures",
]


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
def opq_val(test_values: dict):
    yield OpaqueValues.model_validate(test_values["opaque"])


def mock_register_start_ctx(test_ud: UserData, test_user: User, test_register_id: str):
    class MockRegisterContext(RegisterAppContext):
        @classmethod
        async def get_registration(
            cls, dsrc: Source, register_id: str
        ) -> tuple[UserData, User]:
            if test_register_id == register_id:
                return test_ud, test_user
            raise AppError(
                err_type=ErrorKeys.REGISTER,
                err_desc="Test error",
                debug_key="test_error",
            )

    return MockRegisterContext()


def mock_register_context(server_setup: str, mock_auth_id: str, mock_req_store: dict):
    class MockRegisterContext(RegisterContext):
        @classmethod
        async def get_apake_setup(cls, store: Store) -> str:
            return server_setup

        @classmethod
        async def store_auth_register_state(
            cls, store: Store, user_id: str, state: SavedRegisterState
        ) -> str:
            mock_req_store[mock_auth_id] = state
            return mock_auth_id

    return MockRegisterContext()


def test_start_register(
    test_client, gen_ud_u: tuple[UserData, User], make_cd: Code, opq_val: OpaqueValues
):
    test_ud, test_u = gen_ud_u
    test_register_id = (
        "8c01e95c6021f62f7fc7a0c6149df725129fa4ea846edc1cdc0b13905e880f0c"
    )
    test_auth_id = "9a051d2a4860b9d48624be0206f0743d6ce2f0686cc4cc842d97ea4e51c0b181"
    req_store = {}

    make_cd.app_context.register_ctx = mock_register_start_ctx(
        test_ud, test_u, test_register_id
    )
    make_cd.auth_context.register_ctx = mock_register_context(
        opq_val.server_setup, test_auth_id, req_store
    )

    # password 'clientele'
    req = {
        "email": test_ud.email,
        "client_request": opq_val.client_registration,
        "register_id": test_register_id,
    }

    response = test_client.post("/onboard/register/", json=req)
    res_j = response.json()
    # example state
    # n-aQ8YSkFMbIoTJPS46lBeO4X4v5KbQ52ztB9-xP8wg
    # example message
    # GGnMPMzUGlKDTd0O4Yjw2S3sNrte4a1ybatXCr_-cRvyxVgYqutFLW3oUC5bmAczDl2DMzPRvmukMc-eKmSsZg
    assert res_j["auth_id"] == test_auth_id
    assert response.status_code == codes.OK
    saved_state = SavedRegisterState.model_validate(req_store[test_auth_id])
    assert saved_state.user_id == test_ud.user_id


def mock_register_finish_ctx(
    test_ud: UserData,
    test_user_id: str,
    test_auth_id: str,
    test_register_id: str,
    mock_db: dict,
):
    class MockRegisterContext(RegisterAppContext):
        @classmethod
        async def get_register_state(
            cls, dsrc: Source, auth_id: str
        ) -> SavedRegisterState:
            if auth_id == test_auth_id:
                return SavedRegisterState(user_id=test_user_id)
            raise NoDataError("No data", "test_no_date")

        @classmethod
        async def check_userdata_register(
            cls,
            dsrc: Source,
            register_id: str,
            request_email: str,
            saved_user_id: str,
        ) -> UserData:
            if register_id == test_register_id:
                return test_ud
            raise AppError(
                err_type=ErrorKeys.REGISTER,
                err_desc="Test error",
                debug_key="test_error",
            )

        @classmethod
        async def save_registration(
            cls, dsrc: Source, pw_file: str, new_userdata: UserData
        ) -> None:
            mock_db[new_userdata.user_id] = new_userdata

    return MockRegisterContext()


def test_finish_register(
    test_client,
    faker: Faker,
    gen_ud_u: tuple[UserData, User],
    make_cd: Code,
    opq_val: OpaqueValues,
):
    test_ud, test_u = gen_ud_u
    test_auth_id = "e5a289429121408d95d7e3cde62d0f06da22b86bd49c2a34233423ed4b5e877e"
    test_r_id = "5488f0d6b6534a15"
    mock_db = {}

    make_cd.app_context.register_ctx = mock_register_finish_ctx(
        test_ud, test_ud.user_id, test_auth_id, test_r_id, mock_db
    )

    # password 'clientele'
    bd = faker.date_of_birth(minimum_age=16)
    req = {
        "email": test_ud.email,
        "client_request": opq_val.final_registration,
        "auth_id": test_auth_id,
        "register_id": test_r_id,
        "callname": test_ud.firstname,
        "eduinstitution": "testinstitution",
        "birthdate": bd.isoformat(),
        "age_privacy": True,
    }

    response = test_client.post("/onboard/finish/", json=req)
    # example password file
    """
    DnuCs40tbbcosYBGDyyMrrxNcq-wkzrjZTa65_pJ_QWONK6yr3F4DOLphiBzfmBcTO_icmKmbQps-iBcMiF5CQGnS6qC60tEmF-ffv9Thofssx_y5dix
    Qrch3rCHg_9kMloGndIfuv7n8Sxu8toQD74KIBeOYQfuefdKXy6FGRbvUm4A06OVvkDFtNpkbLNIFkRh2h-m6ZDtMwhXLvBBClz77Jo_jzEYobRL3d-f
    7QrEiZhpehFlN0n5OecMiPFC-g

    n-aQ8YSkFMbIoTJPS46lBeO4X4v5KbQ52ztB9-xP8wgeiTMc52ItDYFQshq4rfw5-WSoIqkg-H2BmoIFQbGBNwE_hacoe5llYjoExc93uFOc7OcGs8gq
    wbgJkWWp40rpC4IeS7WUzh-LwSn6fx2C5Vvx2m9T29U_bD0voDdEMROZi_rAJ1fc8nDvLtahFp91n6_YNkZH0P8289wpUdwfTcpC50gPaWel_TRH8zgK2ZddqO21ZV13d6HjRenRhbjWfw
    """

    assert response.status_code == codes.OK
    new_ud = mock_db[test_ud.user_id]
    assert isinstance(new_ud, UserData)
    assert new_ud.birthdate == bd
