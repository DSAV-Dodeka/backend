from typing import List

from fastapi import APIRouter, Request
from pydantic import TypeAdapter

import apiserver.data.api.ud.birthday
from apiserver import data
from apiserver.app.error import ErrorResponse
from apiserver.app.ops.header import Authorization
from apiserver.app.response import RawJSONResponse
from apiserver.app.routers.helper import require_member
from apiserver.data import Source
from apiserver.lib.model.entities import BirthdayData, UserPointsNamesList

router = APIRouter()

BirthdayList = TypeAdapter(List[BirthdayData])


@router.get("/members/birthdays/", response_model=list[BirthdayData])
async def get_user_birthdays(request: Request, authorization: Authorization):
    dsrc: Source = request.state.dsrc
    await require_member(authorization, dsrc)

    async with data.get_conn(dsrc) as conn:
        birthday_data = await apiserver.data.api.ud.birthday.get_all_birthdays(conn)

    return RawJSONResponse(BirthdayList.dump_json(birthday_data))


@router.get("/members/rankings/{rank_type}")
async def get_user_rankings(rank_type, request: Request, authorization: Authorization):
    dsrc: Source = request.state.dsrc
    await require_member(authorization, dsrc)

    if rank_type not in {"training", "points", "pr"}:
        reason = f"Ranking {rank_type} is unknown!"
        raise ErrorResponse(
            status_code=400,
            err_type="invalid_ranking",
            err_desc=reason,
            debug_key="bad_ranking",
        )

    ranking_data = await data.file.load_json(rank_type)
    return ranking_data


@router.get("/members/class/training")
async def get_training_rankings(request: Request, authorization: Authorization):
    dsrc: Source = request.state.dsrc
    await require_member(authorization, dsrc)


@router.get("/members/classification/{rank_type}")
async def get_classification(rank_type, request: Request, authorization: Authorization):
    dsrc: Source = request.state.dsrc
    await require_member(authorization, dsrc)

    if rank_type not in {"training", "points"}:
        reason = f"Ranking {rank_type} is unknown!"
        raise ErrorResponse(
            status_code=400,
            err_type="invalid_ranking",
            err_desc=reason,
            debug_key="bad_ranking",
        )
    async with data.get_conn(dsrc) as conn:
        class_view = await data.classifications.most_recent_class_of_type(
            conn, rank_type
        )
        user_points = await data.classifications.all_points_in_class(
            conn, class_view.classification_id
        )
    return RawJSONResponse(UserPointsNamesList.dump_json(user_points))
