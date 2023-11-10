import opaquepy.lib as opq
import pytest

import apiserver.lib.utilities as util
from tests.test_util import Fixture


@pytest.fixture(scope="module")
def opaque_setup() -> Fixture[str]:
    yield opq.create_setup()


user_id = "4_person"
password = "abcd"


@pytest.fixture
def gen_pw_file(opaque_setup: str) -> Fixture[str]:
    cl_req, cl_state = opq.register_client(password)
    serv_resp = opq.register(opaque_setup, cl_req, util.usp_hex(user_id))
    cl_fin = opq.register_client_finish(cl_state, password, serv_resp)
    yield opq.register_finish(cl_fin)


def test_login_wrong_pass(gen_pw_file: str, opaque_setup: str):
    cl_msg, cl_state = opq.login_client("wrong")

    serv_resp, serv_state = opq.login(
        opaque_setup, gen_pw_file, cl_msg, util.usp_hex(user_id)
    )

    with pytest.raises(ValueError):
        opq.login_client_finish(cl_state, password, serv_resp)


def test_login_wrong_user_id(gen_pw_file: str, opaque_setup: str):
    cl_msg, cl_state = opq.login_client(password)

    serv_resp, serv_state = opq.login(
        opaque_setup, gen_pw_file, cl_msg, util.usp_hex("wrong")
    )

    with pytest.raises(ValueError):
        opq.login_client_finish(cl_state, password, serv_resp)
