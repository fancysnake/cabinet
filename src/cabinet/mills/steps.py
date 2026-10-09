"""How much of a cast's step budget each part of it spends."""

from math import ceil

from typing_extensions import override

from cabinet.pacts.pulls import Run
from cabinet.pacts.reviews import Picking, Share
from cabinet.pacts.services import StepsProtocol
from cabinet.specs import REVIEW_STEPS, SWEEP_STEPS

# One round is `read`, `plan`, `work` and `answer`.
_ROUND = 4

# The steps every sweep branch walks at most once: `check_clean`,
# `sync_branch`, `merge_base`, `take_pass`, `finish_merge`, `stand_down`,
# `push_work`, `check_ci` or `quality_review`, and `finish_pr`.
_ONCE = 9


# A gate's loop: a whole run and a narrowed one for every repair the bound
# allows, then the last whole run.
def _gates(bound: int) -> int:
    return 2 * bound + 1


# `resolve_conflicts`: one per attempt, and the one that reads the index clean.
def _attempts(bound: int) -> int:
    return bound + 1


class Steps(StepsProtocol):
    # Every step that works no branch. For `review`: `queue_up`, a `pick` per
    # branch and the one that finds the queue empty, and `recap`; for a sweep,
    # `list_prs`, a `next_pr` per branch and the last one, and `report`.
    @override
    def opening(self, queue: int) -> int:
        return queue + 3

    # One round per batch of the `left` threads open, as far as the budget
    # reaches. `None` is a branch the budget has no room for.
    @override
    def review_share(self, picking: Picking, left: int) -> Share | None:
        # What a branch spends besides its rounds: `look`, `land`, `settle`,
        # and the loop of `gates`.
        around = 3 + _gates(picking.bound)
        room = (REVIEW_STEPS - picking.reserved - around) // _ROUND
        if (rounds := min(ceil(left / picking.batch), room)) < 1:
            return None
        return Share(rounds=rounds, steps=around + _ROUND * rounds)

    # The worst one sweep branch can spend, or `None` where the budget has no
    # room for it: the steps walked once, `resolve_conflicts`, and the loop of
    # `gate_check` or `close_gap`.
    @override
    def sweep_share(self, run: Run) -> int | None:
        steps = _ONCE + _attempts(run.bound) + _gates(run.bound)
        if run.reserved + steps > SWEEP_STEPS:
            return None
        return steps
