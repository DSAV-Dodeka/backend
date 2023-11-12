from fastapi import APIRouter


router = APIRouter()


@router.get("/")
async def read_root() -> dict[str, str]:
    return {"Hallo": "Atleten"}
