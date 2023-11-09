import json
from faker import Faker
import pytest

from apiserver.define import DEFINE, grace_period, refresh_exp
from apiserver.lib.hazmat.tokens import BadVerification, verify_access_token
from auth.core.util import dec_b64url, enc_b64url, utc_timestamp
from tests.test_key_token_util import gen_auth_keys, generate_tokens
from tests.test_util import make_test_user


def decode_modify_encode(acc, modification_fn):
    # ChatGPT works pretty well for writing tests
    split_acc = acc.split(".")
    payload = json.loads(dec_b64url(split_acc[1]))
    modified_payload = modification_fn(payload)
    return (
        split_acc[0]
        + "."
        + enc_b64url(json.dumps(modified_payload).encode()).rstrip("=")
        + "."
        + split_acc[2]
    )


def modify_issuer(payload):
    payload["iss"] = "modified_issuer"
    return payload


def test_resource_verify_token(faker: Faker):
    test_user = make_test_user(faker)

    keys = gen_auth_keys("33", "34", "30")
    _, acc, _ = generate_tokens(test_user.user_id, "some", 3424, keys)

    a = verify_access_token(
        acc,
        keys.signing.public,
        grace_period,
        DEFINE.issuer,
        audience=[DEFINE.backend_client_id],
    )
    assert a.sub == test_user.user_id

    utc_now = utc_timestamp() - refresh_exp - 2 * grace_period

    _, acc_exp, _ = generate_tokens(test_user.user_id, "some", 3424, keys, utc_now)

    with pytest.raises(BadVerification) as e:
        verify_access_token(
            acc_exp,
            keys.signing.public,
            grace_period,
            DEFINE.issuer,
            audience=[DEFINE.backend_client_id],
        )
    assert e.value.err_key == "expired_access_token"

    with pytest.raises(BadVerification) as e:
        verify_access_token(
            acc,
            keys.signing.public,
            grace_period,
            "other_issuer",
            audience=[DEFINE.backend_client_id],
        )
    assert e.value.err_key == "bad_token"

    with pytest.raises(BadVerification) as e:
        verify_access_token(
            acc, keys.signing.public, grace_period, DEFINE.issuer, audience=[]
        )
    assert e.value.err_key == "bad_token"

    with pytest.raises(BadVerification) as e:
        verify_access_token(
            "abasz9z85__%7",
            keys.signing.public,
            grace_period,
            DEFINE.issuer,
            audience=[DEFINE.backend_client_id],
        )
    assert e.value.err_key == "decode_error"

    modified_acc = decode_modify_encode(acc, modify_issuer)
    with pytest.raises(BadVerification) as e:
        verify_access_token(
            modified_acc,
            keys.signing.public,
            grace_period,
            DEFINE.issuer,
            audience=[DEFINE.backend_client_id],
        )
    assert e.value.err_key == "invalid_signature"
