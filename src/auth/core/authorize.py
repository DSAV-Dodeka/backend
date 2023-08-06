from urllib.parse import urlencode

from pydantic import ValidationError

import auth.data as data
from auth.core.error import AuthError, RedirectError
from auth.data import DataSource
from auth.core.model import AuthRequest
from auth.core.response import Redirect
from auth.define import Define


def auth_request_validate(
    define: Define,
    response_type,
    client_id,
    redirect_uri,
    state,
    code_challenge,
    code_challenge_method,
    nonce,
) -> AuthRequest:
    if client_id != define.frontend_client_id:
        raise AuthError(
            "invalid_authorization", "Unrecognized client ID!", "bad_client_id"
        )

    if redirect_uri not in define.valid_redirects:
        raise AuthError(
            "invalid_authorization", "Unrecognized redirect for client!", "bad_redirect"
        )

    if response_type != "code":
        raise RedirectError(
            "unsupported_response_type",
            error_desc="Only 'code' response_type is supported!",
        )

    try:
        auth_request = AuthRequest(
            response_type=response_type,
            client_id=client_id,
            redirect_uri=redirect_uri,
            state=state,
            code_challenge=code_challenge,
            code_challenge_method=code_challenge_method,
            nonce=nonce,
        )
    except ValidationError as e:
        raise RedirectError("invalid_request", error_desc=str(e.errors()))

    return auth_request


async def oauth_start(
    response_type: str,
    client_id: str,
    redirect_uri: str,
    state: str,
    code_challenge: str,
    code_challenge_method: str,
    nonce: str,
    dsrc: DataSource,
):
    """This request 'prepares' the authorization request. The client provides the initially required information and
    in this case the endpoint redirects the user-agent to the credentials_url, which will handle the authentication.
    This means that this particular endpoint is not directly in the OAuth 2.1 spec, it is a choice for how to
    authenticate. We already validate the redirect_uri and whether there is a code challenge.

    Any unspecific error in this method should be caught and lead to a server_error redirect.
    """

    auth_request = auth_request_validate(
        dsrc.define,
        response_type,
        client_id,
        redirect_uri,
        state,
        code_challenge,
        code_challenge_method,
        nonce,
    )

    # The retrieval query is any information necessary to get all parameters necessary for the actual request
    retrieval_query = await data.requests.store_auth_request(dsrc, auth_request)

    redirect = (
        f"{dsrc.define.credentials_url}?{urlencode({'persist': retrieval_query})}"
    )

    return Redirect(code=303, url=redirect)


async def oauth_finish(retrieval_query: str, code: str, dsrc: DataSource):
    auth_request = await data.requests.get_auth_request(dsrc, retrieval_query)

    params = {"code": code, "state": auth_request.state}

    redirect = f"{auth_request.redirect_uri}?{urlencode(params)}"

    return Redirect(code=303, url=redirect)
