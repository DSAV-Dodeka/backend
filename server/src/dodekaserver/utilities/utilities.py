import time
import hashlib
import random
import asyncio


def random_time_hash_hex():
    timestamp = time.time_ns().to_bytes(64, byteorder='big')
    random_bytes = timestamp + random.randbytes(8)
    return hashlib.sha256(random_bytes, usedforsecurity=False).digest().hex()
