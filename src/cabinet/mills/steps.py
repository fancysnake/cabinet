"""How much of a cast's step budget each part of it spends."""

from typing_extensions import override

from cabinet.pacts.healing import Run
from cabinet.pacts.services import StepsProtocol
from cabinet.specs import HEAL_STEPS

# The steps every branch walks at most once: `check_clean`, `sync_branch`,
# `merge_base`, `finish_merge` or `stand_down`, `push_work`, `quality_review`
# and `finish_pr`, and `tend` once before each of the four that follow it.
# One push at most: only the merge commits, and the push clears it.
_ONCE = 11


# A gate's loop: a whole run and a narrowed one for every repair the bound
# allows, then the last whole run.
def _gates(bound: int) -> int:
    return 2 * bound + 1


# `resolve_conflicts`: one per attempt, and the one that reads the index clean.
def _attempts(bound: int) -> int:
    return bound + 1


class Steps(StepsProtocol):
    # Every step that works no branch: the muster, a `survey` per branch and
    # the one that finds the queue empty, and `chart`.
    @override
    def opening(self, queue: int) -> int:
        return queue + 3

    # The worst one branch can spend, or `None` where the budget has no room
    # for it: the steps walked once, `resolve_conflicts`, and the loop of
    # `gate_check`.
    @override
    def heal_share(self, run: Run) -> int | None:
        steps = _ONCE + _attempts(run.bound) + _gates(run.bound)
        if run.reserved + steps > HEAL_STEPS:
            return None
        return steps
