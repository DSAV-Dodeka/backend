# from typing import Optional
#
# from apiserver.data import Source, get_kv, DataError, NoDataError
# from apiserver.data.kv import store_kv_perm, store_kv
# from apiserver.data.kv.ops import get_val_kv, pop_kv
#
#
# async def store_string(dsrc: Source, key: str, value: str, expire: int = 1000):
#     if expire == -1:
#         await store_kv_perm(get_kv(dsrc), key, value)
#     else:
#         await store_kv(get_kv(dsrc), key, value, expire)
#
#
# def string_return(value: Optional[bytes]) -> str:
#     if value is None:
#         raise NoDataError(
#             "String for this key does not exist or expired.", "saved_str_empty"
#         )
#     try:
#         return value.decode()
#     except UnicodeEncodeError:
#         raise DataError("Data is not of unicode string type.", "bad_str_encode")
#
#
# async def pop_string(dsrc: Source, key: str) -> str:
#     value = await pop_kv(get_kv(dsrc), key)
#     return string_return(value)
#
#
# async def get_string(dsrc: Source, key: str) -> str:
#     value = await get_val_kv(get_kv(dsrc), key)
#     return string_return(value)
