from apiserver.define import ErrorResponse
from apiserver.define.entities import BirthdayData
from fastapi import APIRouter, Security, Request
import apiserver.data as data
from apiserver.data import Source
from apiserver.auth.header import auth_header
from apiserver.routers.helper import require_member

router = APIRouter()


@router.get("/members/birthdays/", response_model=list[BirthdayData])
async def get_user_birthdays(
    request: Request, authorization: str = Security(auth_header)
):
    dsrc: Source = request.app.state.dsrc
    await require_member(authorization, dsrc)

    async with data.get_conn(dsrc) as conn:
        birthday_data = await data.user.get_all_birthdays(dsrc, conn)
    return birthday_data


@router.get("/members/rankings/{rank_type}")
async def get_user_rankings(
    rank_type, request: Request, authorization: str = Security(auth_header)
):
    dsrc: Source = request.app.state.dsrc
    await require_member(authorization, dsrc)

    if rank_type != "training" and rank_type != "points" and rank_type != "pr":
        reason = f"Ranking {rank_type} is unknown!"
        raise ErrorResponse(
            status_code=400,
            err_type="invalid_ranking",
            err_desc=reason,
            debug_key="bad_ranking",
        )

    ranking_data = await data.file.load_json(rank_type)
    return ranking_data
