from typing import Annotated

from fastapi.params import Security
from fastapi.security.api_key import APIKeyHeader

from apiserver import data
from apiserver.app.define import grace_period, issuer, backend_client_id
from apiserver.app.ops.errors import BadAuth
from apiserver.lib.model.fn.tokens import (
    verify_access_token,
    BadVerification,
    get_kid,
)
from apiserver.data import Source, NoDataError
from apiserver.lib.model.entities import AccessToken

scheme = "Bearer"

# TODO modify APIKeyHeader for better status code
auth_header = APIKeyHeader(name="Authorization", scheme_name=scheme, auto_error=True)

Authorization = Annotated[str, Security(auth_header)]


async def handle_header(authorization: str, dsrc: Source) -> AccessToken:
    if authorization is None:
        raise BadAuth(err_type="invalid_request", err_desc="No authorization provided.")
    if "Bearer " not in authorization:
        raise BadAuth(
            err_type="invalid_request",
            err_desc="Authorization must follow 'Bearer' scheme",
        )
    token = authorization.removeprefix("Bearer ")

    try:
        kid = get_kid(token)
        public_key = await data.trs.key.get_pem_key(dsrc, kid)
        return verify_access_token(
            public_key.public, token, grace_period, issuer, backend_client_id
        )
    except NoDataError as e:
        raise BadAuth(
            err_type="invalid_token",
            err_desc="Key does not exist!",
            debug_key=e.key,
        )
    except BadVerification as e:
        raise BadAuth(
            err_type="invalid_token",
            err_desc="Token verification failed!",
            debug_key=e.err_key,
        )
