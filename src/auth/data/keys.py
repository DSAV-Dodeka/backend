from auth.core.error import UnexpectedDataError
from auth.data.context import token_context
from store import Store
from store.conn import get_kv
from store.kv import get_json
from auth.hazmat.key_decode import aes_from_symmetric
from auth.core.model import KeyState
from auth.hazmat.structs import PEMPrivateKey, A256GCMKey, SymmetricKey
from store.error import NoDataError


async def get_pem_private_key(store: Store, kid_key: str) -> PEMPrivateKey:
    """The kid_key should include any potential suffixes."""
    pem_dict: dict = await get_json(get_kv(store), kid_key)
    if pem_dict is None:
        raise NoDataError("PEM key does not exist.", "pem_private_key_empty")
    return PEMPrivateKey.model_validate(pem_dict)


async def get_symmetric_key(store: Store, kid: str) -> A256GCMKey:
    """Symmetric keys are always private!"""
    symmetric_dict: dict = await get_json(get_kv(store), kid)
    if symmetric_dict is None:
        raise NoDataError("JWK does not exist or expired.", "jwk_empty")
    return A256GCMKey.model_validate(symmetric_dict)


@token_context
async def get_keys(
    store: Store, key_state: KeyState
) -> tuple[SymmetricKey, SymmetricKey, PEMPrivateKey]:
    symmetric_kid = key_state.current_symmetric
    old_symmetric_kid = key_state.old_symmetric
    signing_kid = key_state.current_signing

    # These can throw NoDataError if no key is found
    try:
        # Symmetric key used to verify and encrypt/decrypt refresh tokens
        symmetric_key_data = await get_symmetric_key(store, symmetric_kid)
        old_symmetric_key_data = await get_symmetric_key(store, old_symmetric_kid)
        # Asymmetric private key used for signing access and ID tokens
        # A public key is then used to verify them
        signing_key = await get_pem_private_key(store, signing_kid)
    except NoDataError as e:
        raise UnexpectedDataError(
            "key_not_stored", "One of the token keys was not stored in KV.", e
        )

    symmetric_key = aes_from_symmetric(symmetric_key_data.symmetric)
    old_symmetric_key = aes_from_symmetric(old_symmetric_key_data.symmetric)

    return symmetric_key, old_symmetric_key, signing_key