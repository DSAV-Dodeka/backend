from fastapi import HTTPException, Request
from fastapi.datastructures import Headers

from apiserver.define import DEFINE, grace_period
from apiserver import data
from apiserver.data import Source
from apiserver.lib.resource.error import ResourceError
from apiserver.lib.resource.header import (
    AccessSettings,
    extract_token_and_kid,
    resource_verify_token,
)
from store.error import NoDataError
from apiserver.lib.model.entities import AccessToken

www_authenticate = f"Bearer realm={DEFINE.realm}"


def auth_header(request: Request) -> str:
    # This is so we don't have to instantiate a Request object, which can be annoying
    return parse_auth_header(request.headers)


def parse_auth_header(headers: Headers) -> str:
    authorization = headers.get("Authorization")
    if not authorization:
        # Conforms to RFC6750 https://www.rfc-editor.org/rfc/rfc6750.html
        raise HTTPException(
            status_code=400, headers={"WWW-Authenticate": www_authenticate}
        )

    return authorization


async def verify_token_header(authorization: str, dsrc: Source) -> AccessToken:
    # THROWS ResourceError
    token, kid = extract_token_and_kid(authorization)

    try:
        public_key = (await data.trs.key.get_pem_key(dsrc, kid)).public
    except NoDataError as e:
        raise ResourceError(
            err_type="invalid_token",
            err_desc="Key does not exist!",
            debug_key=e.key,
        )

    access_settings = AccessSettings(
        grace_period=grace_period,
        issuer=DEFINE.issuer,
        aud_client_ids=[DEFINE.backend_client_id],
    )

    # THROWS ResourceError
    return resource_verify_token(token, public_key, access_settings)
