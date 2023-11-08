from typing import Literal, TypeGuard


def is_rank_type(rank_type: str) -> TypeGuard[Literal["training", "points"]]:
    return rank_type in {"training", "points"}
