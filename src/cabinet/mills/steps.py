"""How much of `review`'s step budget each part of the cast spends."""

from math import ceil

from typing_extensions import override

from cabinet.pacts.reviews import Picking, Share
from cabinet.pacts.services import StepsProtocol
from cabinet.specs import STEPS

# One round is `read`, `plan`, `work` and `answer`.
_ROUND = 4


class Steps(StepsProtocol):
    # Every step that works no branch: `queue_up`, a `pick` per branch and the
    # one that finds the queue empty, and `recap`. The forge lists at most a
    # hundred, so this always fits.
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
        room = (STEPS - picking.reserved - around) // _ROUND
        if (rounds := min(ceil(left / picking.batch), room)) < 1:
            return None
        return Share(rounds=rounds, steps=around + _ROUND * rounds)
