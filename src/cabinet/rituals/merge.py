"""Transmutation: ``merge`` brings the base into your branch, gate green.

    vekna cast merge [--plan-only true] [--bound N] [--attended false]

``heal.this`` that works the merge task and no other, the way *Mending* joins
what was split. Only a conflict makes a merge todo, so a branch that is merely
behind is left as it is. The steps live in ``cabinet.gates.ritual.vekna.heal``;
this module is the ritual itself and the surface vekna sweeps.
"""

from vekna.lexicon import attended, ritual

from cabinet.gates.ritual.vekna.heal import (
    answer_gate,
    answer_threads,
    ask_triage,
    chart,
    check_clean,
    close_gap,
    finish_merge,
    finish_pr,
    gate_check,
    job_gate,
    land_answers,
    land_job,
    mend_job,
    merge_base,
    muster_mine,
    muster_pr,
    muster_this,
    pick_job,
    post_answers,
    push_work,
    quality_review,
    read_threads,
    rerun_jobs,
    resolve_conflicts,
    set_aside,
    settle_left,
    skip_pr,
    stand_down,
    summon,
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
        bound=components.bound,
        attended=attended() and components.attended,
        tasks=components.working("merge"),
    )


__all__ = [
    "answer_gate",
    "answer_threads",
    "ask_triage",
    "chart",
    "check_clean",
    "close_gap",
    "finish_merge",
    "finish_pr",
    "gate_check",
    "job_gate",
    "land_answers",
    "land_job",
    "mend_job",
    "merge",
    "merge_base",
    "muster_mine",
    "muster_pr",
    "muster_this",
    "pick_job",
    "post_answers",
    "push_work",
    "quality_review",
    "read_threads",
    "rerun_jobs",
    "resolve_conflicts",
    "set_aside",
    "settle_left",
    "skip_pr",
    "stand_down",
    "summon",
    "survey",
    "sync_branch",
    "tend",
]
