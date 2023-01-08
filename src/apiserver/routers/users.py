from apiserver.define.entities import BirthdayData
from fastapi import APIRouter, Security, Request
import apiserver.data as data
from apiserver.data import Source
from apiserver.auth.header import auth_header
from apiserver.routers.helper import require_member

router = APIRouter()


@router.get("/members/birthdays/", response_model=list[BirthdayData])
async def get_user_birthdays(request: Request, authorization: str = Security(auth_header)):
    dsrc: Source = request.app.state.dsrc
    await require_member(authorization, dsrc)

    async with data.get_conn(dsrc) as conn:
        birthday_data = await data.user.get_all_birthdays(dsrc, conn)
    return birthday_data


@router.get("/members/rankings_training/", response_model=object)
async def get_user_rankings(request: Request, authorization: str = Security(auth_header)):
    dsrc: Source = request.app.state.dsrc
    await require_member(authorization, dsrc)

    ranking_data = await data.user.get_all_rankings("training")
    return ranking_data


@router.get("/members/rankings_pr/", response_model=object)
async def get_user_rankings(request: Request, authorization: str = Security(auth_header)):
    dsrc: Source = request.app.state.dsrc
    await require_member(authorization, dsrc)

    ranking_data = await data.user.get_all_rankings("pr")
    return ranking_data


@router.get("/members/rankings_general/", response_model=object)
async def get_user_rankings(request: Request, authorization: str = Security(auth_header)):
    dsrc: Source = request.app.state.dsrc
    await require_member(authorization, dsrc)

    ranking_data = await data.user.get_all_rankings("general")
    return ranking_data
