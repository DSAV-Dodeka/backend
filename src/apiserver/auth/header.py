from fastapi.security.api_key import APIKeyHeader

from apiserver.define.entities import AccessToken
from apiserver import data
from apiserver.data import Source, NoDataError
from apiserver.auth.tokens import verify_access_token, BadVerification, get_kid

scheme = "Bearer"

# TODO modify APIKeyHeader for better status code
auth_header = APIKeyHeader(name="Authorization", scheme_name=scheme, auto_error=True)


class BadAuth(Exception):
    """ Error during handling header. """
    def __init__(self, status_code: int, err_type: str, err_desc: str, debug_key: str = ""):
        self.status_code = status_code
        self.err_type = err_type
        self.err_desc = err_desc
        self.debug_key = debug_key


async def handle_header(authorization: str, dsrc: Source) -> AccessToken:
    if authorization is None:
        raise BadAuth(400, err_type="invalid_request", err_desc="No authorization provided.")
    if "Bearer " not in authorization:
        raise BadAuth(400, err_type="invalid_request", err_desc="Authorization must follow 'Bearer' scheme")
    token = authorization.removeprefix("Bearer ")

    try:
        kid = get_kid(token)
        public_key = await data.kv.get_pem_key(dsrc, kid)
        return verify_access_token(public_key.public, token)
    except NoDataError as e:
        raise BadAuth(401, err_type="invalid_token", err_desc="Key does not exist!", debug_key=e.key)
    except BadVerification as e:
        raise BadAuth(401, err_type="invalid_token", err_desc="Token verification failed!", debug_key=e.err_key)
