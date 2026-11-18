"""The `[cabinet]` table, from every place vekna reads config.

vekna merges it: the user's table for the project, the project's own
`.vekna.toml`, then what the user sets for every project, key by key. Which
project the cwd belongs to is vekna's to say.
"""

from pydantic import ValidationError
from vekna.lexicon import config_table

from cabinet.pacts.project import KEYS, ConfigError, Project

_TABLE = "cabinet"


# Only the keys the ritual reads are checked, so a refused value under a key
# another ritual reads does not stop this cast. A key `Project` does not hold
# is kept, and so refused: it may be a needed one misspelt.
def read_project(needs: frozenset[str]) -> Project:
    table = config_table(_TABLE)
    read = {
        key: value
        for key, value in table.values.items()
        if key in needs or key not in KEYS
    }
    try:
        return Project.model_validate(read)
    except ValidationError as error:
        msg = f"{', '.join(table.sources)}: {error}"
        raise ConfigError(msg) from error
