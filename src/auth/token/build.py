import secrets
from secrets import token_urlsafe
from typing import Type
from auth.data.relational.user import IdUserData

from auth.token.build_util import encode_token_dict, decode_refresh, add_info_to_id
from auth.core.model import RefreshToken, IdTokenBase, AccessTokenBase
from auth.hazmat.structs import PEMPrivateKey, SymmetricKey
from auth.data.relational.entities import SavedRefreshToken
from auth.token.crypt_token import encrypt_refresh
from auth.token.sign_token import sign_id_token, sign_access_token


def build_refresh_save(
    saved_refresh: SavedRefreshToken, utc_now: int, id_userdata_type: Type[IdUserData]
) -> tuple[AccessTokenBase, IdTokenBase, IdUserData, str, str, str, SavedRefreshToken]:
    """Use old refresh token and create a new refresh token with a different nonce. id_info_model is generic, because
    the application level decides what it looks like."""
    # Rebuild access and ID tokens from value in refresh token
    # We need the core static info to rebuild with new iat, etc.
    saved_access, saved_id_token, id_userdata = decode_refresh(
        saved_refresh, id_userdata_type
    )
    user_id = saved_id_token.sub

    # Scope to be returned in response
    access_scope = saved_access.scope

    # Nonce is used to make it impossible to 'guess' new refresh tokens
    # (So it becomes a combination of family_id + id nr + nonce)
    # Although signing and encrypting should also protect it from that
    new_nonce = token_urlsafe(16).rstrip("=")
    # We don't store the access tokens and refresh tokens in the final token
    # To construct new tokens, we need that information so we save it in the DB
    new_refresh_save = SavedRefreshToken(
        family_id=saved_refresh.family_id,
        access_value=saved_refresh.access_value,
        id_token_value=saved_refresh.id_token_value,
        exp=saved_refresh.exp,
        iat=utc_now,
        nonce=new_nonce,
        user_id=saved_refresh.user_id,
    )

    return (
        saved_access,
        saved_id_token,
        id_userdata,
        user_id,
        access_scope,
        new_nonce,
        new_refresh_save,
    )


def build_refresh_token(
    new_refresh_id: int,
    saved_refresh: SavedRefreshToken,
    new_nonce: str,
    refresh_key: SymmetricKey,
) -> str:
    # The actual refresh token is an encrypted JSON dictionary containing the id,
    # family_id and nonce
    refresh = RefreshToken(
        id=new_refresh_id, family_id=saved_refresh.family_id, nonce=new_nonce
    )
    refresh_token = encrypt_refresh(refresh_key, refresh)
    return refresh_token


def create_tokens(
    user_id: str,
    scope: str,
    auth_time: int,
    id_nonce: str,
    utc_now: int,
    id_userdata: IdUserData,
    issuer: str,
    frontend_client_id: str,
    backend_client_id: str,
    refresh_exp: int,
) -> tuple[AccessTokenBase, IdTokenBase, str, SavedRefreshToken]:
    """
    Builds the required structures and encodes information for the refresh token.

    Args:
        user_id: `sub` claim
        scope: scope string that will be added as `scope` claim
        auth_time: time that user was authenticated
        id_nonce: nonce value for ID token
        utc_now: timestamp that will be used for the token's `iat` value
        id_userdata: contains any additional data that needs to be added to ID token
        issuer: `iss` claim
        frontend_client_id: used for the audience of the access and id tokens
        backend_client_id: used for the audience of the access token
        refresh_exp: the time that will be added to utc_now to compute the token's `exp` value

    Returns:
        A tuple of newly built access token, ID token, scope and refresh token. They are not yet fully formed and need
        to be finished.
    """
    # Build new tokens
    access_token_data, id_token_core_data = id_access_tokens(
        sub=user_id,
        iss=issuer,
        aud_access=[frontend_client_id, backend_client_id],
        aud_id=[frontend_client_id],
        scope=scope,
        auth_time=auth_time,
        id_nonce=id_nonce,
    )

    # Scope to be returned in response
    access_scope = access_token_data.scope

    # Encoded tokens to store for refresh token
    access_val_encoded = encode_token_dict(access_token_data.model_dump())
    id_token_dict = add_info_to_id(id_token_core_data, id_userdata)
    id_token_val_encoded = encode_token_dict(id_token_dict)
    # Each authentication creates a refresh token of a particular family, which
    # has a static lifetime
    family_id = secrets.token_urlsafe(16)
    refresh_save = SavedRefreshToken(
        family_id=family_id,
        access_value=access_val_encoded,
        id_token_value=id_token_val_encoded,
        exp=utc_now + refresh_exp,
        iat=utc_now,
        nonce="",
        user_id=user_id,
    )
    return access_token_data, id_token_core_data, access_scope, refresh_save


def finish_tokens(
    refresh_id: int,
    refresh_save: SavedRefreshToken,
    refresh_key: SymmetricKey,
    access_token_data: AccessTokenBase,
    id_token_data: IdTokenBase,
    id_userdata: IdUserData,
    utc_now: int,
    signing_key: PEMPrivateKey,
    access_exp: int,
    id_exp: int,
    *,
    nonce: str,
) -> tuple[str, str, str]:
    """Encrypts and signs the tokens and adds the time information to them."""
    refresh = RefreshToken(id=refresh_id, family_id=refresh_save.family_id, nonce=nonce)
    # This function performs encryption of the refresh token
    # ! Calls cryptographic primitives
    refresh_token = encrypt_refresh(refresh_key, refresh)

    # This function adds exp and signing time info and signs the access token using the signing key
    # ! Calls the PyJWT library
    access_token = sign_access_token(
        signing_key, access_token_data, utc_now, access_exp
    )
    # This function adds exp and signing time info as well as id_info and signs the id token using the signing key
    # ! Calls the PyJWT library
    id_token = sign_id_token(signing_key, id_token_data, id_userdata, utc_now, id_exp)

    return refresh_token, access_token, id_token


def id_access_tokens(
    sub: str,
    iss: str,
    aud_access: list[str],
    aud_id: list[str],
    scope: str,
    auth_time: int,
    id_nonce: str,
) -> tuple[AccessTokenBase, IdTokenBase]:
    """Create ID and access token objects."""
    access_core = AccessTokenBase(sub=sub, iss=iss, aud=aud_access, scope=scope)
    id_core = IdTokenBase(
        sub=sub,
        iss=iss,
        aud=aud_id,
        auth_time=auth_time,
        nonce=id_nonce,
    )

    return access_core, id_core
