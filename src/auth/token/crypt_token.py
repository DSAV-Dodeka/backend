from pydantic import ValidationError

from auth.core.error import InvalidRefresh
from auth.core.model import RefreshToken
from auth.hazmat.crypt_dict import encrypt_dict, decrypt_dict, DecryptError
from auth.hazmat.structs import SymmetricKey


def encrypt_refresh(symmetric_key: SymmetricKey, refresh: RefreshToken) -> str:
    return encrypt_dict(symmetric_key.private, refresh.model_dump())


def decrypt_refresh(symmetric_key: SymmetricKey, refresh_token: str) -> RefreshToken:
    refresh_dict = decrypt_dict(symmetric_key.private, refresh_token)
    return RefreshToken.model_validate(refresh_dict)


def decrypt_old_refresh(
    symmetric_key: SymmetricKey,
    old_symmetric_key: SymmetricKey,
    old_refresh_token: str,
    tried_old: bool = False,
) -> RefreshToken:
    # expects base64url-encoded binary
    try:
        # If it has been tampered with, this will also give an error
        old_refresh = decrypt_refresh(symmetric_key, old_refresh_token)
    except DecryptError:
        # Retry with previous key
        if not tried_old:
            return decrypt_old_refresh(
                old_symmetric_key, old_symmetric_key, old_refresh_token, True
            )
        # Problem with the key cryptography
        raise InvalidRefresh("InvalidToken")
    except ValidationError:
        # From parsing the dict
        raise InvalidRefresh("Bad validation")
    except ValueError:
        # For example from the JSON decoding
        raise InvalidRefresh("Other parsing")

    return old_refresh
