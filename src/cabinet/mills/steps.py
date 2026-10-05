"""How much of a cast's step budget each part of it spends."""

from math import ceil

from typing_extensions import override

from cabinet.pacts.pulls import Run
from cabinet.pacts.reviews import Picking, Share
from cabinet.pacts.services import StepsProtocol
from cabinet.specs import REVIEW_STEPS, SWEEP_STEPS

# One round is `read`, `plan`, `work` and `answer`.
_ROUND = 4


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
    def share(self, picking: Picking, left: int) -> Share | None:
        # What a branch spends besides its rounds: `look`, `land`, `settle`,
        # and `gates` — a whole run and a narrowed one for every repair the
        # bound allows, then the last whole run.
        around = 2 * picking.bound + 4
        room = (REVIEW_STEPS - picking.reserved - around) // _ROUND
        if (rounds := min(ceil(left / picking.batch), room)) < 1:
            return None
        return Share(rounds=rounds, steps=around + _ROUND * rounds)

    # The worst one sweep branch can spend, or `None` where the budget has no
    # room for it. Eight steps every branch walks at most once — `check_clean`,
    # `sync_branch`, `merge_base`, `take_pass`, `finish_merge`, `stand_down`,
    # `push_work`, and `check_ci` or `quality_review` — then `finish_pr`; a
    # `resolve_conflicts` per attempt and the one that reads the index clean;
    # and the gate's loop, `gate_check` or `close_gap`: a whole run and a
    # narrowed one for every repair the bound allows, then the last whole run.
    @override
    def sweep_share(self, run: Run) -> int | None:
        steps = 9 + (run.bound + 1) + (2 * run.bound + 1)
        if run.reserved + steps > SWEEP_STEPS:
            return None
        return steps
