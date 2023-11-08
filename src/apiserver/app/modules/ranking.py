from typing import Optional


from apiserver.app.error import ErrorKeys, AppError
from apiserver.data import Source
from apiserver.data.api.classifications import events_in_class
from apiserver.data.context.app_context import RankingContext, conn_wrap
from apiserver.data.context.ranking import context_most_recent_class_id_of_type
from apiserver.data.source import source_session
from apiserver.data.special import user_events_in_class
from apiserver.lib.logic.ranking import is_rank_type
from apiserver.lib.model.entities import ClassEvent, UserEvent
from datacontext.context import ctxlize_wrap


async def class_id_or_recent(
    dsrc: Source, ctx: RankingContext, class_id: Optional[int], rank_type: Optional[str]
) -> int:
    if class_id is not None:
        return class_id
    elif rank_type is None:
        reason = "Provide either class_id or rank_type query parameter!"
        raise AppError(
            err_type=ErrorKeys.GET_CLASS,
            err_desc=reason,
            debug_key="user_events_invalid_class",
        )
    elif not is_rank_type(rank_type):
        reason = f"Ranking {rank_type} is unknown!"
        raise AppError(
            err_type=ErrorKeys.GET_CLASS,
            err_desc=reason,
            debug_key="user_events_bad_ranking",
        )
    else:
        class_id = await context_most_recent_class_id_of_type(ctx, dsrc, rank_type)

        return class_id


async def mod_user_events_in_class(
    dsrc: Source,
    ctx: RankingContext,
    user_id: str,
    class_id: Optional[int],
    rank_type: Optional[str],
) -> list[UserEvent]:
    async with source_session(dsrc) as session:
        sure_class_id = await class_id_or_recent(session, ctx, class_id, rank_type)

        user_events = await ctxlize_wrap(user_events_in_class, conn_wrap)(
            ctx, session, user_id, sure_class_id
        )

    return user_events


async def mod_events_in_class(
    dsrc: Source,
    ctx: RankingContext,
    class_id: Optional[int] = None,
    rank_type: Optional[str] = None,
) -> list[ClassEvent]:
    async with source_session(dsrc) as session:
        sure_class_id = await class_id_or_recent(session, ctx, class_id, rank_type)

        events = await ctxlize_wrap(events_in_class, conn_wrap)(
            ctx, session, sure_class_id
        )

    return events
