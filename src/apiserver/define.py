import os
from pathlib import Path
from typing import Any, Optional

import tomllib
from jinja2 import Environment, FileSystemLoader, select_autoescape

from apiserver.resources import res_path
from auth.define import (
    Define as AuthDefine,
    default_define,
    grace_period,
    email_expiration,
    id_exp,
    access_exp,
    refresh_exp,
)

__all__ = [
    "grace_period",
    "email_expiration",
    "id_exp",
    "access_exp",
    "refresh_exp",
    "LOGGER_NAME",
    "DEFINE",
    "loc_dict",
]

LOGGER_NAME = "backend"


class Define(AuthDefine):
    allowed_envs: set[str]


def load_define(define_path_name: Optional[os.PathLike[Any]] = None) -> Define:
    if define_path_name is None:
        config = dict()
    else:
        define_path_resolved = Path(define_path_name)

        with open(define_path_resolved, "rb") as f:
            config = tomllib.load(f)

    define_dict = (
        default_define | config
    )  # override default values with config variables

    return Define.model_validate(define_dict)


def load_loc(loc_path_name: os.PathLike[Any]) -> dict[str, Any]:
    loc_path_resolved = Path(loc_path_name)

    with open(loc_path_resolved, "rb") as f:
        loc_loaded = tomllib.load(f)

    return loc_loaded


define_path = res_path.joinpath("define.toml")
loc_path = res_path.joinpath("loc.toml")

DEFINE = load_define(define_path)
loc_dict = load_loc(loc_path)

template_env = Environment(
    loader=FileSystemLoader(res_path.joinpath("templates")),
    autoescape=select_autoescape(),
)
