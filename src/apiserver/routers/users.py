from fastapi import APIRouter, Request

from apiserver import data
from apiserver.auth.header import Authorization
from apiserver.data import Source
from apiserver.define import ErrorResponse
from apiserver.define.entities import BirthdayData
from apiserver.routers.helper import require_member, handle_auth

router = APIRouter()


@router.get("/members/birthdays/", response_model=list[BirthdayData])
async def get_user_birthdays(request: Request, authorization: Authorization):
    dsrc: Source = request.state.dsrc
    await require_member(authorization, dsrc)

    async with data.get_conn(dsrc) as conn:
        birthday_data = await data.user.get_all_birthdays(conn)
    return birthday_data


@router.get("/members/rankings/{rank_type}")
async def get_user_rankings(rank_type, request: Request, authorization: Authorization):
    dsrc: Source = request.state.dsrc
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


@router.get("/members/easter_eggs/get/count")
async def get_user_easter_eggs_count(request: Request, authorization: Authorization):
    dsrc: Source = request.state.dsrc
    acc = await handle_auth(authorization, dsrc)

    async with data.get_conn(dsrc) as conn:
        easter_eggs_get_count_data = await data.user.get_easter_eggs_count(
            conn, acc.sub
        )

    # Count all the found eggs and return total?
    return easter_eggs_get_count_data.count()


@router.get("/members/easter_eggs/found/{easter_egg_id}")
async def user_easter_egg_found(
    easter_egg_id, request: Request, authorization: Authorization
):
    dsrc: Source = request.state.dsrc
    acc = await handle_auth(authorization, dsrc)

    async with data.get_conn(dsrc) as conn:
        # Function needs to be implemented, insert into database
        await data.user.found_easter_egg(conn, acc.sub, easter_egg_id)

    return "To be implemented.."
