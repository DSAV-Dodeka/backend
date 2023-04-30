import logging

from fastapi import APIRouter

from apiserver.app.define import LOGGER_NAME

router = APIRouter()

logger = logging.getLogger(LOGGER_NAME)


@router.get("/")
async def read_root():
    return {"Hallo": "Atleten"}
