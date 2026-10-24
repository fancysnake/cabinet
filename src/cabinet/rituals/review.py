"""Divination: ``review`` posts the quality review on your pull request.

    vekna cast review [--plan-only true] [--attended true]

``heal.this`` that works the review task and no other. A pull request wearing
the reviewed label has had its review; take the label off to ask again. The
steps live in ``cabinet.gates.ritual.vekna.heal``; this module is the ritual
itself and the surface vekna sweeps.
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


@ritual("review", max_steps=HEAL_STEPS)
def review(components: Heal) -> MusterThis:
    return MusterThis(
        project=services().project(),
        bound=components.bound,
        attended=components.attended,
        tasks=components.working("review"),
    )


__all__ = [
    "chart",
    "check_clean",
    "finish_merge",
    "finish_pr",
    "gate_check",
    "merge_base",
    "muster_mine",
    "muster_this",
    "push_work",
    "quality_review",
    "resolve_conflicts",
    "review",
    "set_aside",
    "skip_pr",
    "stand_down",
    "survey",
    "sync_branch",
    "tend",
]
