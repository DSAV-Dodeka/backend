from typing import Optional

import time
import hashlib
import random
import math


def random_time_hash_hex(extra_seed: Optional[bytes] = None):
    """ Random string (bound to timestamp and optional extra seed) to represent events/objects that must be uniquely
    identified. """
    timestamp = time.time_ns().to_bytes(64, byteorder='big')
    random_bytes = (extra_seed if extra_seed is not None else b'') + timestamp + random.randbytes(8)
    return hashlib.sha256(random_bytes, usedforsecurity=False).digest().hex()


urlsafe = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-"

rad64_dict = urlsafe + "~"


# urlsafe-preserving hex
def usp_hex(unicode_str: str):
    """ It is nice to internally use an urlsafe (i.e. only using characters that don't have to be percent-encoded (e.g.
    @ becomes %40) representations of Unicode usernames that preserves some common, urlsafe characters, making it more
    readable. It might be a good idea to write accelerated Python extensions for this in the future if it proves to be
    slow. """
    anp_base64url_str = ''
    hexable = ''
    anp_seq = True
    for c in unicode_str:
        if c in urlsafe:
            if anp_seq:
                anp_base64url_str += c
            else:
                if hexable:
                    anp_base64url_str += hexable.encode('utf-8').hex()
                    hexable = ''
                anp_base64url_str += ('~' + c)
                anp_seq = True
        else:
            if anp_seq:
                anp_seq = False
                anp_base64url_str += '~~'
            hexable += c
    if hexable:
        anp_base64url_str += hexable.encode('utf-8').hex()

    return anp_base64url_str


def de_usp_hex(usp_hex_str: str):
    """ Reverse of usp_hex, returns the utf-8 string. """
    unicode_str = ''
    prev_empty = False
    parts = usp_hex_str.split('~')
    for part in parts:
        if not part:  # empty due to ~~
            prev_empty = True
        elif prev_empty:  # non-empty and following ~~, so non-urlsafe
            unicode_str += str(bytes.fromhex(part), 'utf-8')
            prev_empty = False
        else:  # non-empty not following ~~, so urlsafe
            unicode_str += part

    return unicode_str


"""START LICENSED CODE
Copyright (c) 2012 Kevin Gillette. All rights reserved.
Licensed under BSD 3-Clause "New" or "Revised" License

This code has been modified."""

urlsafe_table = dict((c, i) for i, c in enumerate(rad64_dict))


def _rad64_enc(n: int) -> str:
    out = ''
    while n > 0:
        out = rad64_dict[n & 63] + out
        n >>= 6
    return out


def _rad64_dec(rad64_cs: str) -> int:
    n = 0
    for c in rad64_cs:
        got_c = urlsafe_table.get(c)
        if got_c is None:
            raise ValueError("Invalid character in input: " + c)
        n = n << 6 | got_c
    return n


"""END LICENSED CODE"""


def rad64_frombytes(b: bytes):
    return _rad64_enc(int.from_bytes(b, byteorder='big'))


def rad64_tobytes(s: str) -> bytes:
    by = _rad64_dec(s)
    byte_len = math.ceil(by.bit_length() / 8)
    return by.to_bytes(byteorder='big', length=byte_len)


def usp_hex_bin(usp_hex_str: str) -> bytes:
    return rad64_tobytes(usp_hex_str)


def usp_hex_debin(usp_hex_bytes: bytes) -> str:
    return rad64_frombytes(usp_hex_bytes)


def random_user_time_hash_hex(user_usph: str):
    return random_time_hash_hex(usp_hex_bin(user_usph))

