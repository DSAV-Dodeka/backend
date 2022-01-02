from fastapi import APIRouter, HTTPException, status, Security
from fastapi.security.api_key import APIKeyHeader

import dodekaserver.data as data
from dodekaserver.auth.tokens import verify_access_token

dsrc = data.dsrc

router = APIRouter()

scheme = "Bearer"

# TODO modify APIKeyHeader for better status code
auth_header = APIKeyHeader(name="Authorization", scheme_name=scheme, auto_error=True)


@router.get("/res/profile")
async def get_profile(authorization: str = Security(auth_header)):
    # if authorization is None:
    #     authorization = auth
    print(authorization)
    if authorization is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="No authorization provided.")
    if "Bearer " not in authorization:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authorization must follow 'Bearer' "
                                                                             "scheme")
    token = authorization.removeprefix("Bearer ")
    public_key = await data.key.get_token_public(dsrc)
    acc = verify_access_token(public_key, token)
    return {
        "username": acc.sub,
        "scope": acc.scope
    }
