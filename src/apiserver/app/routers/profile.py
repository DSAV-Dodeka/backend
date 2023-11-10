from fastapi import APIRouter
from apiserver.app.dependencies import RequireMember, SourceDep

from apiserver.data.api.ud.userdata import get_userdata_by_id
from apiserver.lib.model.entities import UserData

from apiserver import data

router = APIRouter()


@router.get("/res/profile/")
async def get_profile(dsrc: SourceDep, member: RequireMember) -> UserData:
    async with data.get_conn(dsrc) as conn:
        user_data = await get_userdata_by_id(conn, member.sub)

    return user_data
