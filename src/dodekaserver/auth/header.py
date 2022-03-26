from fastapi import HTTPException, status
from fastapi.security.api_key import APIKeyHeader

from dodekaserver import data
from dodekaserver.data.entities import AccessToken
from dodekaserver.auth.tokens import verify_access_token, BadVerification

dsrc = data.dsrc

scheme = "Bearer"

# TODO modify APIKeyHeader for better status code
auth_header = APIKeyHeader(name="Authorization", scheme_name=scheme, auto_error=True)


class BadAuth(Exception):
    """ Error during handling header. """
    def __init__(self, status_code: int, err_type: str, err_desc: str):
        self.status_code = status_code
        self.err_type = err_type
        self.err_desc = err_desc


async def handle_header(authorization: str) -> AccessToken:
    if authorization is None:
        raise BadAuth(400, err_type="invalid_request", err_desc="No authorization provided.")
    if "Bearer " not in authorization:
        raise BadAuth(400, err_type="invalid_request", err_desc="Authorization must follow 'Bearer' scheme")
    token = authorization.removeprefix("Bearer ")
    public_key = await data.key.get_token_public(dsrc)
    try:
        return verify_access_token(public_key, token)
    except BadVerification as e:
        raise BadAuth(401, err_type="invalid_token", err_desc=e.err_type)