import asyncio
from pathlib import Path

import opaquepy as opq
import pytest
import pytest_asyncio
from faker import Faker
from httpx import AsyncClient
from httpx import codes

import apiserver.utilities as util
from apiserver import data

from apiserver.define.entities import SignedUp
from apiserver.data import Source
from apiserver.data.user import new_userdata
from apiserver.data.classifications import insert_classification
from apiserver.auth.tokens import create_tokens, finish_tokens
from apiserver.auth.tokens_data import get_keys
from apiserver.env import load_config
from apiserver.utilities.crypto import encrypt_dict, aes_from_symmetric, decrypt_dict


@pytest.fixture(scope="module", autouse=True)
def event_loop():
    """Necessary for async tests with module-scoped fixtures"""
    loop = asyncio.get_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="module")
def api_config():
    test_config_path = Path(__file__).parent.joinpath("localdead.toml")
    yield load_config(test_config_path)


@pytest_asyncio.fixture(scope="module")
async def local_client():
    async with AsyncClient(base_url="http://localhost:4243/") as local_client:
        yield local_client


@pytest.mark.asyncio
async def test_root(local_client):
    response = await local_client.get("/")

    assert response.status_code == codes.OK
    assert response.json() == {"Hallo": "Atleten"}


@pytest.mark.asyncio
async def test_onboard_signup(local_client):
    req = {
        "firstname": "mr",
        "lastname": "person",
        "email": "hi@xs.nl",
        "phone": "+31068243",
    }

    response = await local_client.post("/onboard/signup/", json=req)
    print(response.json())


@pytest_asyncio.fixture(scope="module")
async def local_dsrc(api_config):
    dsrc = Source()
    dsrc.init_gateway(api_config)
    await dsrc.startup(api_config)
    yield dsrc


@pytest_asyncio.fixture(scope="module")
async def admin_access(local_dsrc):
    admin_id = "admin_test"
    scope = "member admin"
    utc_now = util.utc_timestamp()

    access_token_data, id_token_data, access_scope, refresh_save = create_tokens(
        admin_id, scope, utc_now, "test_nonce", utc_now
    )
    refresh_id = 5252626
    aesgcm, signing_key = await get_keys(local_dsrc)
    refresh_token, access_token, id_token = finish_tokens(
        refresh_id,
        refresh_save,
        aesgcm,
        access_token_data,
        id_token_data,
        utc_now,
        signing_key,
        nonce="",
    )
    yield access_token


@pytest.mark.asyncio
async def test_generate_admin():
    admin_password = "admin"
    # async with data.get_conn(local_dsrc) as conn:
    #     setup = await data.opaquesetup.get_setup(conn)

    setup = ""

    cl_req, cl_state = opq.register_client(admin_password)
    serv_resp = opq.register(setup, cl_req, util.usp_hex("0_admin"))
    cl_fin = opq.register_client_finish(cl_state, admin_password, serv_resp)
    pw_file = opq.register_finish(cl_fin)

    print(pw_file)


@pytest.mark.asyncio
async def test_generate_dummies(local_dsrc: Source, faker: Faker):
    admin_password = "admin"
    async with data.get_conn(local_dsrc) as conn:
        setup = await data.opaquesetup.get_setup(conn)

    # setup = ""
    faker_u = faker.unique

    for i in range(99):
        fname = faker_u.first_name()
        lname = faker_u.last_name()
        email = f"{fname}.{lname}@gmail.com"
        su = SignedUp(
            firstname=fname,
            lastname=lname,
            email=email,
            phone=faker_u.phone_number(),
            confirmed=True,
        )
        av40id = int.from_bytes(faker_u.binary(2), byteorder="big")
        register_id = util.random_time_hash_hex()
        joined = faker.date()
        async with data.get_conn(local_dsrc) as conn:
            uid = await data.user.new_user(
                local_dsrc,
                conn,
                su,
                register_id=register_id,
                av40id=av40id,
                joined=joined,
            )
            userdata = new_userdata(su, uid, register_id, av40id, joined)

            cl_req, cl_state = opq.register_client(admin_password)
            serv_resp = opq.register(setup, cl_req, uid)
            cl_fin = opq.register_client_finish(cl_state, admin_password, serv_resp)
            pw_file = opq.register_finish(cl_fin)
            birthdate = faker.date()
            new_ud = data.user.finished_userdata(
                userdata,
                callname=fname,
                eduinstitution="TU Delft",
                birthdate=birthdate,
                show_age=True,
            )

            await data.user.update_password_file(conn, uid, pw_file)
            await data.user.upsert_userdata(conn, new_ud)
            await data.signedup.delete_signedup(conn, email)

@pytest.mark.asyncio
async def test_bulk(local_dsrc):
    async with data.get_conn(local_dsrc) as conn:
        await insert_classification(conn)


@pytest.mark.asyncio
async def test_generate_rand():
    x = util.random_time_hash_hex(short=True)
    print(x)


@pytest.mark.asyncio
async def test_delete(local_dsrc: Source):
    async with data.get_conn(local_dsrc) as conn:
        await data.user.delete_user(conn, "4_t_tb")


@pytest.mark.asyncio
async def test_fill_signedup():
    key_set_dict = {
        "keys": [
            {
                "kid": "886011ae1466e872",
                "kty": "oct",
                "k": "hpPUuT_feql5Qo-1emMMlvkd50HSoTAiGKOUNZO2KZA",
                "alg": "A256GCM",
                "use": "enc",
            },
            {
                "kid": "54e45c5a068effb1",
                "kty": "oct",
                "k": "E5Nw5-kXR542pWVyNy9lXiD7W46YV4sF-njX9biUBng",
                "alg": "A256GCM",
                "use": "enc",
            },
            {
                "kid": "2dadb3af386b4d9d",
                "alg": "EdDSA",
                "kty": "okp",
                "crv": "Ed448",
                "x": "f5538Oa3cLDNVLcsZI_SLwYSZuM6Vn_5rV5iVi7IcRqoAQ9Ne5w9Nhy9uPZGVzQeZz5T0xYrx4mA",
                "d": "JXpGIitdCa1PqlbFPY50pIunS5AiTz0OCai92WRWfC4-82r74uk-pIqKbk1Wv11dkcEP8gnACbZy",
                "use": "sig",
            },
        ]
    }

    # key_set: JWKSet = JWKSet.parse_obj(key_set_dict)
    runtime_key = aes_from_symmetric("AT_av0v62Z3hQH50VYwKBks1-VSukK9xDN_Ur34mdZ4")
    reencrypted_key_set = encrypt_dict(runtime_key, key_set_dict)
    decrypt_dict(runtime_key, reencrypted_key_set)
    print(reencrypted_key_set)


@pytest.mark.asyncio
async def test_onboard_confirm(local_client: AsyncClient, admin_access):
    req = {
        "email": "comcom@dsavdodeka.nl",
        "av40id": "+31068243",
        "joined": "2022-04-03",
    }
    headers = {"Authorization": f"Bearer {admin_access}"}
    response = await local_client.post("/onboard/confirm/", json=req, headers=headers)
    print(response.json())
