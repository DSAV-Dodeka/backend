from store.kv import store_json_multi, get_json, store_json_perm
from apiserver.data import get_kv, Source, NoDataError
from apiserver.lib.model.entities import PEMKey, A256GCMKey, JWKSet


async def store_pem_keys(dsrc: Source, keys: list[PEMKey]):
    keys_to_store = {f"{key.kid}-pem": key.model_dump() for key in keys}

    await store_json_multi(get_kv(dsrc), keys_to_store)


async def store_symmetric_keys(dsrc: Source, keys: list[A256GCMKey]):
    keys_to_store = {key.kid: key.model_dump() for key in keys}

    await store_json_multi(get_kv(dsrc), keys_to_store)


async def store_jwks(dsrc: Source, value: JWKSet):
    await store_json_perm(get_kv(dsrc), "jwk_set", value.model_dump())


async def get_jwks(dsrc: Source, kid: str):
    jwks_dict: dict = await get_json(get_kv(dsrc), kid)
    if jwks_dict is None:
        raise NoDataError("JWK does not exist or expired.", "jwk_empty")
    return JWKSet.model_validate(jwks_dict)


async def get_pem_key(dsrc: Source, kid: str) -> PEMKey:
    pem_dict: dict = await get_json(get_kv(dsrc), f"{kid}-pem")
    if pem_dict is None:
        raise NoDataError("PEM key does not exist.", "pem_key_empty")
    return PEMKey.model_validate(pem_dict)


async def get_symmetric_key(dsrc: Source, kid: str) -> A256GCMKey:
    symmetric_dict: dict = await get_json(get_kv(dsrc), kid)
    if symmetric_dict is None:
        raise NoDataError("JWK does not exist or expired.", "jwk_empty")
    return A256GCMKey.model_validate(symmetric_dict)
