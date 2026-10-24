"""Transmutation: ``merge`` brings the base into your branch, gate green.

    vekna cast merge [--bound N] [--attended true]

``heal.this`` that works the merge task and no other, the way *Mending* joins
what was split. Only a conflict makes a merge todo, so a branch that is merely
behind is left as it is. The steps live in ``cabinet.gates.ritual.vekna.heal``;
this module is the ritual itself and the surface vekna sweeps.
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
from cabinet.pacts.heal import MusterThis
from cabinet.pacts.healing import Heal
from cabinet.pacts.services import services
from cabinet.specs import HEAL_STEPS


@ritual("merge", max_steps=HEAL_STEPS)
def merge(components: Heal) -> MusterThis:
    return MusterThis(
        project=services().project(),
        plan_only=components.plan_only,
        bound=components.bound,
        attended=components.attended,
        tasks=["merge"],
    )


__all__ = [
    "chart",
    "check_clean",
    "finish_merge",
    "finish_pr",
    "gate_check",
    "merge",
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
