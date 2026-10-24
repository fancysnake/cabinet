"""Abjuration: ``ci`` makes your branch's red CI jobs green.

    vekna cast ci [--plan-only true] [--bound N] [--attended true]

``heal.this`` that works the ci task and no other, the way *Lesser
Restoration* ends one condition at a time. Only a red check on a job in
``[cabinet.ci.jobs]`` makes a ci todo. The steps live in
``cabinet.gates.ritual.vekna.heal``; this module is the ritual itself and the
surface vekna sweeps.
"""

from vekna.lexicon import ritual

from cabinet.gates.ritual.vekna.heal import (
    chart,
    check_clean,
    close_gap,
    finish_merge,
    finish_pr,
    gate_check,
    job_gate,
    land_job,
    mend_job,
    merge_base,
    muster_mine,
    muster_this,
    pick_job,
    push_work,
    quality_review,
    rerun_jobs,
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


@ritual("ci", max_steps=HEAL_STEPS)
def ci(components: Heal) -> MusterThis:
    return MusterThis(
        project=services().project(),
        bound=components.bound,
        attended=components.attended,
        tasks=components.working("ci"),
    )


__all__ = [
    "chart",
    "check_clean",
    "ci",
    "close_gap",
    "finish_merge",
    "finish_pr",
    "gate_check",
    "job_gate",
    "land_job",
    "mend_job",
    "merge_base",
    "muster_mine",
    "muster_this",
    "pick_job",
    "push_work",
    "quality_review",
    "rerun_jobs",
    "resolve_conflicts",
    "set_aside",
    "skip_pr",
    "stand_down",
    "survey",
    "sync_branch",
    "tend",
]
