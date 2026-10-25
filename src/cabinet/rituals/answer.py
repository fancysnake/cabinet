"""Enchantment: ``answer`` settles the review threads on your branch with you.

    vekna cast answer [--plan-only true] [--bound N] --attended true [--batch N]

``heal.this`` that works the answer task and no other, the way *Command* puts
one word to each listener. Only an unresolved review thread makes an answer
todo, and only an attended cast works it: unattended, the report says how many
threads wait. The steps live in ``cabinet.gates.ritual.vekna.heal``; this
module is the ritual itself and the surface vekna sweeps.
"""

from vekna.lexicon import ritual

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
    survey,
    sync_branch,
    tend,
)
from cabinet.pacts.heal import MusterThis
from cabinet.pacts.healing import Heal
from cabinet.pacts.services import services
from cabinet.specs import HEAL_STEPS


@ritual("answer", max_steps=HEAL_STEPS)
def answer(components: Heal) -> MusterThis:
    return MusterThis(
        project=services().project(),
        bound=components.bound,
        attended=components.attended,
        batch=components.batch,
        tasks=components.working("answer"),
    )


__all__ = [
    "answer",
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
    "merge_base",
    "muster_mine",
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
    "survey",
    "sync_branch",
    "tend",
]
