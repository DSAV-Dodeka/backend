from typing import Optional

from fastapi import APIRouter

import dodekaserver.data as data

dsrc = data.dsrc

router = APIRouter()


@router.get("/users/{user_id}")
async def get_user(user_id: int):
    user = await data.get_user_row(dsrc, user_id)

    return {"user": str(user)}


@router.get("/user_write/{user_id}")
async def write_user(user_id: int, name: Optional[str], last_name: Optional[str]):
    user_row = {"id": user_id, "name": name, "last_name": last_name}
    rc = await data.upsert_user_row(dsrc, user_row)
    return {"Response": "Ok"}


@router.get("/")
async def read_root():
    return {"Hallo": "Atleten"}
