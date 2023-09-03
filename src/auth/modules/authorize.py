from yarl import URL

from auth import data
from auth.core.error import AuthError
from auth.validate.authorize import auth_request_validate
from auth.core.response import Redirect
from store.error import NoDataError
from auth.define import Define
from store import Store


async def oauth_start(
    define: Define,
    store: Store,
    response_type: str,
    client_id: str,
    redirect_uri: str,
    state: str,
    code_challenge: str,
    code_challenge_method: str,
    nonce: str,
) -> Redirect:
    """This request 'prepares' the authorization request. The client provides the initially required information and
    in this case the endpoint redirects the user-agent to the credentials_url, which will handle the authentication.
    This means that this particular endpoint is not directly in the OAuth 2.1 spec, it is a choice for how to
    authenticate. We already validate the redirect_uri and whether there is a code challenge.

    Any unspecific error in this method should be caught and lead to a server_error redirect.
    """

    auth_request = auth_request_validate(
        define,
        response_type,
        client_id,
        redirect_uri,
        state,
        code_challenge,
        code_challenge_method,
        nonce,
    )

    # The retrieval query is any information necessary to get all parameters necessary for the actual request
    flow_id = await data.authorize.store_auth_request(store, auth_request)

    url = URL(define.credentials_url)

    redirect = str(url.update_query({"flow_id": flow_id}))

    return Redirect(code=303, url=redirect)


async def oauth_callback(store: Store, retrieval_query: str, code: str) -> Redirect:
    try:
        auth_request = await data.authorize.get_auth_request(store, retrieval_query)
    except NoDataError:
        raise AuthError(
            "invalid_request",
            "Expired or missing auth request",
            "missing_oauth_flow_id",
        )

    params = {"code": code, "state": auth_request.state}
    redirect = str(URL(auth_request.redirect_uri).update_query(params))

    return Redirect(code=303, url=redirect)
