"""
Define differs from env/config in that it should include only PUBLIC constants which should not differ on the
deployment environment SPECIFICS and should be known far ahead of time. Changing these can also lead to tokens
breaking, while that should not happen for env/config settings.
"""

from typing import Any
from pydantic import BaseModel


# See below for appropriate values for specific environments
class Define(BaseModel):
    frontend_client_id: str
    valid_redirects: set[str]
    api_root: str
    issuer: str
    backend_client_id: str
    credentials_url: str
    signup_url: str
    onboard_email: str
    # realm as in the realm for WWW-Authenticate
    realm: str


# On the client we refresh if ID is almost expired
# By setting it lower than the access token's expiry, we make reduce the risk of requests made too close to each
# other with an expired access token. This can lead to problems due to refresh token rotation.

id_exp = 55 * 60  # 55 minutes
# access_exp = 5
access_exp = 1 * 60 * 60  # 1 hour
refresh_exp = 30 * 24 * 60 * 60  # 1 month

# grace_period = 1
grace_period = 3 * 60  # 3 minutes in which it is still accepted

email_expiration = 15 * 60


default_define: dict[str, Any] = {}
