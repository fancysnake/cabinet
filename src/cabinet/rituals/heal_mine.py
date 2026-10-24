"""Evocation: ``heal.mine`` takes each of your pull requests as far as it goes.

    vekna cast heal.mine [--plan-only true] [--bound N] [--attended true]

Every open pull request of yours not wearing the wait label, oldest-modified
first. The steps live in ``cabinet.gates.ritual.vekna.heal``, shared with
``heal.this`` and the task rituals; this module is the ritual itself and the
surface vekna sweeps. Every step is exported, so the facade names the whole
graph it casts.
"""

from vekna.lexicon import ritual

from cabinet.gates.ritual.vekna.heal import (
    chart,
    check_clean,
    finish_merge,
    finish_pr,
    gate_check,
    merge_base,
    muster_mine,
    muster_this,
    push_work,
    quality_review,
    resolve_conflicts,
    set_aside,
    skip_pr,
    stand_down,
    survey,
    sync_branch,
    tend,
)
from cabinet.pacts.heal import MusterMine
from cabinet.pacts.healing import Heal
from cabinet.pacts.services import services
from cabinet.specs import HEAL_STEPS


@ritual("heal.mine", max_steps=HEAL_STEPS)
def heal_mine(components: Heal) -> MusterMine:
    return MusterMine(
        project=services().project(),
        tasks=components.working(),
        bound=components.bound,
        attended=components.attended,
    )


__all__ = [
    "chart",
    "check_clean",
    "finish_merge",
    "finish_pr",
    "gate_check",
    "heal_mine",
    "merge_base",
    "muster_mine",
    "muster_this",
    "push_work",
    "quality_review",
    "resolve_conflicts",
    "set_aside",
    "skip_pr",
    "stand_down",
    "survey",
    "sync_branch",
    "tend",
]
