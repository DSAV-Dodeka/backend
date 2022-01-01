from fastapi import APIRouter

import dodekaserver.data as data

dsrc = data.dsrc

router = APIRouter()


@router.get("/")
async def read_root():
    return {"Hallo": "Atleten"}
