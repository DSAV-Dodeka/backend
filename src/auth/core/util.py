import hashlib
import secrets
import time


def random_time_hash_hex(
    extra_seed: bytes | str | None = None, short: bool = False
) -> str:
    """Random string (bound to timestamp and optional extra seed) to represent events/objects that must be uniquely
    identified. These should not be used for security."""
    if isinstance(extra_seed, str):
        extra_seed = extra_seed.encode("utf-8")

    timestamp = time.time_ns().to_bytes(10, byteorder="big")
    random_bytes = (
        (extra_seed if extra_seed is not None else b"")
        + secrets.token_bytes(10)
        + timestamp
    )
    hashed = hashlib.shake_256(random_bytes)
    if short:
        return hashed.hexdigest(8)
    else:
        return hashed.hexdigest(16)
