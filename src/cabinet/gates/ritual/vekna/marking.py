"""Putting a ritual's checkpoint on the board.

Every ritual that marks one marks it the same way, and only the ritual's name
and where the pull request number comes from differ — so the call lives here
and each step brings its own two.
"""

from cabinet.pacts.forge import ForgeError
from cabinet.pacts.project import Marked, Project, State
from cabinet.pacts.services import services


# Best-effort and never fatal: a checkpoint is a board marker, and losing one
# is not worth abandoning the work it marks. What the forge made of it comes
# back for the caller to put wherever that step says things — a delta, or the
# branch's row.
async def mark(project: Project, *, number: int, ritual: Marked, state: State) -> str:
    add, remove = project.labels.pair(ritual, state)
    try:
        await services().forge(project).label(number, add=[add], remove=[remove])
    except ForgeError as error:
        return f"could not mark {add}: {error}"
    return ""
