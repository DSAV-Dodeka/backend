from store.kv import store_json_multi, get_json, store_json_perm
from apiserver.data import get_kv, Source
from store.error import NoDataError
from apiserver.lib.model.entities import PEMKey, JWKSet
from auth.hazmat.structs import A256GCMKey, PEMPrivateKey

pem_suffix = "-pem"
pem_private_suffix = "-pem-private"


async def store_pem_keys(
    dsrc: Source, keys: list[PEMKey], private_keys: list[PEMPrivateKey]
) -> None:
    keys_to_store = {f"{key.kid}{pem_suffix}": key.model_dump() for key in keys}
    private_keys_to_store = {
        f"{key.kid}{pem_private_suffix}": key.model_dump() for key in private_keys
    }

    await store_json_multi(get_kv(dsrc), keys_to_store)
    await store_json_multi(get_kv(dsrc), private_keys_to_store)


async def store_symmetric_keys(dsrc: Source, keys: list[A256GCMKey]) -> None:
    keys_to_store = {key.kid: key.model_dump() for key in keys}

    await store_json_multi(get_kv(dsrc), keys_to_store)


async def store_jwks(dsrc: Source, value: JWKSet) -> None:
    await store_json_perm(get_kv(dsrc), "jwk_set", value.model_dump())


async def get_jwks(dsrc: Source, kid: str) -> JWKSet:
    jwks_dict = await get_json(get_kv(dsrc), kid)
    if jwks_dict is None:
        raise NoDataError("JWK does not exist or expired.", "jwk_empty")
    return JWKSet.model_validate(jwks_dict)


async def get_pem_key(dsrc: Source, kid: str) -> PEMKey:
    pem_dict = await get_json(get_kv(dsrc), f"{kid}{pem_suffix}")
    if pem_dict is None:
        raise NoDataError("PEM public key does not exist.", "pem_public_key_empty")
    return PEMKey.model_validate(pem_dict)
