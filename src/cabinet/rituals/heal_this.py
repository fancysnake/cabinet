"""Evocation: ``heal.this`` takes your branch's pull request as far as it goes.

    vekna cast heal.this [--plan-only true] [--bound N] [--attended true]

The pull request of the branch at the cwd. The steps live in
``cabinet.gates.ritual.vekna.heal``, shared with ``heal.mine`` and the task
rituals; this module is the ritual itself and the surface vekna sweeps.
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


@ritual("heal.this", max_steps=HEAL_STEPS)
def heal_this(components: Heal) -> MusterThis:
    return MusterThis(
        project=services().project(),
        plan_only=components.plan_only,
        bound=components.bound,
        attended=components.attended,
    )


__all__ = [
    "chart",
    "check_clean",
    "finish_merge",
    "finish_pr",
    "gate_check",
    "heal_this",
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
