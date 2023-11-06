import json
from typing import Any

from apiserver.resources import res_path


async def load_json(filename: str) -> dict[str, Any]:
    pth = res_path.joinpath(filename + ".json")
    if not pth.exists():
        fakedata = {
            "points": [
                {"Naam": "Arnold", "Punten": 12},
                {"Naam": "Arnold", "Punten": 12},
                {"Naam": "Arnold", "Punten": 12},
            ]
        }

        with open(pth, "x") as f:
            json.dump(fakedata, f)

    with open(pth, "r") as fj:
        data = json.load(fj)

    if not isinstance(data, dict):
        raise ValueError("Data is not JSON!")

    return data
