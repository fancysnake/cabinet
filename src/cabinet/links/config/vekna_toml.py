"""The `[cabinet]` section of the repository's `.vekna.toml`.

Found the way vekna finds it — by walking up from the cwd — so a cast started
anywhere in the repository reads the same file vekna loaded the rituals from.
"""

import tomllib
from typing import TYPE_CHECKING

from pydantic import BaseModel, ValidationError

from cabinet.pacts.project import ConfigError, Project

if TYPE_CHECKING:
    from pathlib import Path

_NAME = ".vekna.toml"


# The rest of the file is vekna's; only this section is read, and a missing
# one means the defaults.
class _VeknaToml(BaseModel):
    cabinet: Project = Project()


def read_project(start: Path) -> Project:
    for directory in (start, *start.parents):
        named = directory / _NAME
        if named.is_file():
            return _read(named)
    msg = f"no {_NAME} found from {start} upwards"
    raise ConfigError(msg)


def _read(named: Path) -> Project:
    with named.open("rb") as handle:
        data = tomllib.load(handle)
    try:
        return _VeknaToml.model_validate(data).cabinet
    except ValidationError as error:
        msg = f"{named}: [cabinet] {error}"
        raise ConfigError(msg) from error
