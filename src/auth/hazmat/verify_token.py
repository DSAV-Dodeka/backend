from auth.core.error import InvalidRefresh
from auth.core.model import RefreshToken
from auth.data.relational.entities import SavedRefreshToken

FIRST_SIGN_TIME = 1640690242


def verify_refresh(
    saved_refresh: SavedRefreshToken,
    old_refresh: RefreshToken,
    utc_now: int,
    grace_period: int,
) -> None:
    if (
        saved_refresh.nonce != old_refresh.nonce
        or saved_refresh.family_id != old_refresh.family_id
    ):
        raise InvalidRefresh("Bad comparison")
    elif saved_refresh.iat > utc_now or saved_refresh.iat < FIRST_SIGN_TIME:
        # sanity check
        raise InvalidRefresh
    elif utc_now > saved_refresh.exp + grace_period:
        # refresh no longer valid
        raise InvalidRefresh
