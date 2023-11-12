from faker import Faker
from fastapi import HTTPException
from fastapi.datastructures import Headers
import pytest
from apiserver.app.dependencies import require_admin, require_member, verify_user
from apiserver.app.error import ErrorResponse

from apiserver.app.ops.header import parse_auth_header
from apiserver.define import DEFINE, grace_period, refresh_exp
from apiserver.lib.resource.error import ResourceError
from apiserver.lib.resource.header import AccessSettings, resource_verify_token
from auth.core.util import utc_timestamp
from tests.test_key_token_util import gen_auth_keys, generate_tokens
from tests.test_util import acc_token_from_info, make_test_user


def test_auth_test():
    test_auth_val = "some"
    fake_headers = Headers(headers={"Authorization": test_auth_val})
    assert parse_auth_header(fake_headers) == test_auth_val

    empty_headers = Headers()
    with pytest.raises(HTTPException) as e:
        parse_auth_header(empty_headers)

    assert e.value.headers is not None
    assert "WWW-Authenticate" in e.value.headers


@pytest.mark.asyncio
async def test_require_admin(faker: Faker):
    test_user = make_test_user(faker)

    acc1 = acc_token_from_info(test_user.user_id, scopes="admin")
    acc2 = acc_token_from_info(test_user.user_id, scopes="admi")
    acc3 = acc_token_from_info(test_user.user_id, scopes="not anadmin")
    acc4 = acc_token_from_info(test_user.user_id, scopes="admin alsoelse")

    with pytest.raises(ErrorResponse):
        await require_admin(acc2)

    with pytest.raises(ErrorResponse):
        await require_admin(acc3)

    assert acc1 == await require_admin(acc1)
    assert acc4 == await require_admin(acc4)


@pytest.mark.asyncio
async def test_require_member(faker: Faker):
    test_user = make_test_user(faker)

    acc1 = acc_token_from_info(test_user.user_id, scopes="admin member")
    acc2 = acc_token_from_info(test_user.user_id, scopes="admi")
    acc3 = acc_token_from_info(test_user.user_id, scopes="amember")
    acc4 = acc_token_from_info(test_user.user_id, scopes="member")

    with pytest.raises(ErrorResponse):
        await require_member(acc2)

    with pytest.raises(ErrorResponse):
        await require_member(acc3)

    assert acc1 == await require_member(acc1)
    assert acc4 == await require_member(acc4)


def test_verify_user(faker: Faker):
    test_user = make_test_user(faker)

    acc1 = acc_token_from_info(test_user.user_id, scopes="d1")
    acc2 = acc_token_from_info(test_user.user_id + "else", scopes="d2")
    acc3 = acc_token_from_info(test_user.user_id + "_really", scopes="d3 d4 ")
    acc4 = acc_token_from_info(test_user.user_id, scopes="d55@2")

    with pytest.raises(ErrorResponse):
        verify_user(acc2, test_user.user_id)

    with pytest.raises(ErrorResponse):
        verify_user(acc3, test_user.user_id)

    assert verify_user(acc1, test_user.user_id) is True
    assert verify_user(acc4, test_user.user_id) is True


def test_resource_verify_token(faker: Faker):
    test_user = make_test_user(faker)

    keys = gen_auth_keys("33", "34", "30")
    _, acc, _ = generate_tokens(test_user.user_id, "some", 3424, keys)

    acc_sett = AccessSettings(
        issuer=DEFINE.issuer,
        grace_period=grace_period,
        aud_client_ids=[DEFINE.backend_client_id],
    )

    a = resource_verify_token(acc, keys.signing.public, acc_sett)
    assert a.sub == test_user.user_id

    utc_now = utc_timestamp() - refresh_exp - 2 * grace_period

    _, acc, _ = generate_tokens(test_user.user_id, "some", 3424, keys, utc_now)

    with pytest.raises(ResourceError) as e:
        resource_verify_token(acc, keys.signing.public, acc_sett)

    assert e.value.debug_key == "expired_access_token"
