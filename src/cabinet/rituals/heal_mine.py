"""Evocation: ``heal.mine`` queues a ``heal.pr`` for each pull request with work.

    vekna cast heal.mine [--plan-only true] [--bound N] [--batch N]

Every open pull request of yours not wearing the wait label, oldest-modified
first, is surveyed, and this cast works none of them itself: each one with
work goes to a ``heal.pr`` of its own, queued on the daemon, which runs it in a pooled
worktree beside the others. The cast stays until every one of them has ended,
then reports their rows as its own and fails where any branch was blocked.
With no daemon listening it says so and fails.
The steps live in ``cabinet.gates.ritual.vekna.heal``, shared with
``heal.this`` and the task rituals; this module is the ritual itself and the
surface vekna sweeps. ``heal.pr`` is exported beside it: a project loading
only this facade can still run what it queues.
"""

from vekna.lexicon import ritual

from cabinet.gates.ritual.vekna.heal import mustered
from cabinet.pacts.heal import MusterMine
from cabinet.pacts.healing import Heal
from cabinet.rituals.heal_pr import heal_pr
from cabinet.specs import HEAL_STEPS


@ritual("heal.mine", max_steps=HEAL_STEPS)
def heal_mine(components: Heal) -> MusterMine:
    return mustered(MusterMine, components)


__all__ = ["heal_mine", "heal_pr"]
