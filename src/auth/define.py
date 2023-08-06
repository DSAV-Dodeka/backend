"""
Define differs from env/config in that it should include only PUBLIC constants which should not differ on the
deployment environment SPECIFICS and should be known far ahead of time. Changing these can also lead to tokens
breaking, while that should not happen for env/config settings.
"""

from typing import Optional

import os
from pathlib import Path
import tomli

from pydantic import BaseModel


# See below for appropriate values for specific environments
class Define(BaseModel):
    credentials_url: str
    frontend_client_id: str
    valid_redirects: set[str]


default_define = {}


def load_define(define_path_name: Optional[os.PathLike] = None) -> Define:
    define_path = Path(define_path_name)

    with open(define_path, "rb") as f:
        config = tomli.load(f)

    define = default_define | config  # override default values with config variables

    return Define.model_validate(define)
