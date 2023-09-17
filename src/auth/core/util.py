import binascii
import hashlib
import json
import secrets
import time
from base64 import urlsafe_b64decode, urlsafe_b64encode
from datetime import datetime, timezone
from typing import Any, Optional


def utc_timestamp() -> int:
    return int(datetime.now(timezone.utc).timestamp())


class DecodeError(ValueError):
    pass


def dec_b64url(s: str) -> bytes:
    """
    Decodes a base64url-encoded string to bytes.

    It works with either padding or no padding. It simply ignores any
    characters that are not part of the base64url alphabet. If it uses the standard '+' or '/' it will interpret them
    as if standard base64 is used. It WILL fail if the number of characters is 1 more than a multiple of 4 or if there
    is data after any added padding.
    """
    try:
        b64_bytes = add_base64_padding(s).encode("utf-8")
        return urlsafe_b64decode(b64_bytes)
    except binascii.Error:
        raise DecodeError


def add_base64_padding(unpadded: str) -> str:
    while len(unpadded) % 4 != 0:
        unpadded += "="
    return unpadded


def enc_b64url(b: bytes) -> str:
    """
    Encodes bytes to a base64url-encoded string with no padding.
    """
    return urlsafe_b64encode(b).decode("utf-8").rstrip("=")


def enc_dict(dct: dict[str, Any]) -> bytes:
    """Convert dict to UTF-8-encoded bytes in JSON format."""
    return json.dumps(dct).encode("utf-8")


def dec_dict(encoded: bytes) -> dict[str, Any]:
    """Convert UTF-8 bytes containing JSON to a dict."""
    decoded = encoded.decode("utf-8")
    try:
        obj = json.loads(decoded)
    except json.decoder.JSONDecodeError:
        raise DecodeError(f"Error decoding JSON: {decoded}")
    if not isinstance(obj, dict):
        raise DecodeError("Only supports JSON objects, not primitives.")
    return obj


def random_time_hash_hex(
    extra_seed: Optional[bytes | str] = None, short: bool = False
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
