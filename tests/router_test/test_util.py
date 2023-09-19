from dataclasses import dataclass

from faker import Faker
from pydantic import BaseModel

from apiserver.lib.model.entities import IdInfo
from apiserver.lib.utilities import gen_id_name
from auth.core.model import AuthRequest


def cr_user_id(id_int: int, g_id_name: str):
    return f"{id_int}_{g_id_name}"


@dataclass
class GenUser:
    id_int: int
    user_id: str
    user_email: str


class OpaqueValues(BaseModel):
    server_setup: str
    login_start_request: str
    fake_password_file: str
    correct_password_file: str
    login_start_state: str


def make_test_user(faker: Faker):
    user_fn = faker.first_name()
    user_ln = faker.last_name()
    test_user_id_int = faker.random_int(min=3, max=300)
    test_id_name = gen_id_name(user_fn, user_ln)
    test_user_id = cr_user_id(test_user_id_int, test_id_name)
    test_user_email = faker.email()

    return GenUser(
        id_int=test_user_id_int, user_id=test_user_id, user_email=test_user_email
    )


def make_extended_test_user(faker: Faker):
    user_fn = faker.first_name()
    user_ln = faker.last_name()
    test_user_id_int = faker.random_int(min=3, max=300)
    test_id_name = gen_id_name(user_fn, user_ln)
    test_user_id = cr_user_id(test_user_id_int, test_id_name)
    test_user_email = faker.email()

    test_user = GenUser(
        id_int=test_user_id_int, user_id=test_user_id, user_email=test_user_email
    )
    return test_user, IdInfo(
        email=test_user_email,
        name=user_fn + " " + user_ln,
        given_name=user_fn,
        family_name=user_ln,
        nickname=user_fn,
        preferred_username=user_fn,
        birthdate=faker.date_of_birth(minimum_age=16).isoformat(),
    )


mock_redirect = "http://localhost:3000/auth/callback"
mock_auth_request = AuthRequest(
    response_type="code",
    client_id="dodekaweb_client",
    redirect_uri=mock_redirect,
    state="KV6A2hTOv6mOFYVpTAOmWw",
    code_challenge="8LNMS54GS7iB7H67U5OFLclCl0F87vy5uf-Izj3TCdQ",
    code_challenge_method="S256",
    nonce="-eB2lpr1IqZdJzt9CfDZ5jrHGa6yE87UUTFd4CWweOI",
)


class KeyValues(BaseModel):
    symmetric: str
    signing_public: str
    signing_private: str
