from fastapi import APIRouter
from apiserver.app.dependencies import RequireMember, SourceDep

from apiserver.lib.model.entities import UserData
from apiserver.app.routers.members import get_profile as get_profile_members

router = APIRouter()


@router.get("/res/profile/")
async def get_profile(dsrc: SourceDep, member: RequireMember) -> UserData:
    return await get_profile_members(dsrc, member)
