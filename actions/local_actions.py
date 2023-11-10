import asyncio
from pathlib import Path

import opaquepy as opq
import pytest
import pytest_asyncio
from faker import Faker
from apiserver.data.context.ranking import add_new_event

import apiserver.lib.utilities as util
import auth.core.util
from apiserver import data
from apiserver.app.ops.startup import get_keystate
from apiserver.data import Source, get_conn
from apiserver.data.api.classifications import insert_classification, UserPoints
from apiserver.data.api.ud.userdata import new_userdata
from apiserver.data.special import update_class_points
from apiserver.define import DEFINE
from apiserver.env import load_config
from apiserver.lib.model.entities import NewEvent, SignedUp, UserNames
from auth.data.authentication import get_apake_setup
from auth.data.keys import get_keys
from auth.data.relational.opaque import get_setup
from auth.data.relational.user import EmptyIdUserData
from auth.define import refresh_exp, access_exp, id_exp
from auth.token.build import create_tokens, finish_tokens
from datacontext.context import DontReplaceContext
from store import Store


@pytest.fixture(scope="session", autouse=True)
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
async def local_dsrc(api_config):
    store = Store()
    store.init_objects(api_config)
    dsrc = Source()
    dsrc.store = store
    await store.startup()
    yield dsrc


@pytest_asyncio.fixture(scope="module")
async def admin_access(local_dsrc):
    admin_id = "admin_test"
    scope = "member admin"
    utc_now = auth.core.util.utc_timestamp()
    id_userdata = EmptyIdUserData()
    access_token_data, id_token_data, access_scope, refresh_save = create_tokens(
        admin_id,
        scope,
        utc_now - 1,
        "test_nonce",
        utc_now,
        id_userdata,
        DEFINE.issuer,
        DEFINE.frontend_client_id,
        DEFINE.backend_client_id,
        refresh_exp,
    )
    refresh_id = 5252626
    key_state = await get_keystate(local_dsrc)
    keys = await get_keys(DontReplaceContext(), local_dsrc.store, key_state)
    refresh_token, access_token, id_token = finish_tokens(
        refresh_id,
        refresh_save,
        keys.symmetric,
        access_token_data,
        id_token_data,
        id_userdata,
        utc_now,
        keys.signing,
        access_exp,
        id_exp,
        nonce="",
    )
    yield access_token


@pytest.mark.asyncio
async def test_get_admin_token(admin_access):
    print(admin_access)


@pytest.mark.asyncio
async def test_generate_admin(local_dsrc):
    admin_password = "admin"
    setup = await get_apake_setup(DontReplaceContext(), local_dsrc.store)

    cl_req, cl_state = opq.register_client(admin_password)
    serv_resp = opq.register(setup, cl_req, util.usp_hex("0_admin"))
    cl_fin = opq.register_client_finish(cl_state, admin_password, serv_resp)
    pw_file = opq.register_finish(cl_fin)

    print(pw_file)


@pytest.mark.asyncio
async def test_generate_dummies(local_dsrc: Source, faker: Faker):
    admin_password = "admin"
    async with data.get_conn(local_dsrc) as conn:
        setup = await get_setup(conn)

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
        register_id = auth.core.util.random_time_hash_hex()
        joined = faker.date()
        async with data.get_conn(local_dsrc) as conn:
            uid = await data.user.new_user(
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
            new_ud = data.ud.finished_userdata(
                userdata,
                callname=fname,
                eduinstitution="TU Delft",
                birthdate=birthdate,
                show_age=True,
            )

            await data.user.UserOps.update_password_file(conn, uid, pw_file)
            await data.ud.upsert_userdata(conn, new_ud)
            await data.signedup.delete_signedup(conn, email)


@pytest.mark.asyncio
async def test_generate_rand():
    x = auth.core.util.random_time_hash_hex(short=True)
    print(x)


@pytest.mark.asyncio
async def test_add_classification(local_dsrc):
    async with get_conn(local_dsrc) as conn:
        await insert_classification(conn, "training")


@pytest.mark.asyncio
async def test_update_points(local_dsrc):
    async with get_conn(local_dsrc) as conn:
        training_class = await data.classifications.most_recent_class_of_type(
            conn, "training"
        )
        points_class = await data.classifications.most_recent_class_of_type(
            conn, "points"
        )
        await update_class_points(conn, training_class.classification_id)
        await update_class_points(conn, points_class.classification_id)


@pytest.mark.asyncio
async def test_add_event(local_dsrc, faker: Faker):
    faker.seed_instance(3)
    async with get_conn(local_dsrc) as conn:
        users = await data.ud.get_all_usernames(conn)

    events_users = 15
    if len(users) < events_users:
        events_users = len(users)

    chosen_users: list[UserNames] = faker.random_elements(
        users, length=events_users, unique=True
    )
    point_amount = 13

    user_points = [
        UserPoints(user_id=u.user_id, points=point_amount) for u in chosen_users
    ]
    fake_words = "_".join(faker.words(3))

    new_event = NewEvent(
        users=user_points,
        class_type="points",
        date=faker.date_this_month(),
        event_id=fake_words,
        category="cool catego242ry",
        description="desc",
    )

    await add_new_event(DontReplaceContext(), local_dsrc, new_event)
