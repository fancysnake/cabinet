"""Evocation: ``heal.mine`` takes each of your pull requests as far as it goes.

    vekna cast heal.mine [--plan-only true] [--bound N] [--attended false] [--batch N]

Every open pull request of yours not wearing the wait label, oldest-modified
first. The steps live in ``cabinet.gates.ritual.vekna.heal``, shared with
``heal.this`` and the task rituals; this module is the ritual itself and the
surface vekna sweeps. Every step is exported, so the facade names the whole
graph it casts.
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
from cabinet.pacts.heal import MusterMine
from cabinet.pacts.healing import Heal
from cabinet.pacts.services import services
from cabinet.specs import HEAL_STEPS


@ritual("heal.mine", max_steps=HEAL_STEPS)
def heal_mine(components: Heal) -> MusterMine:
    return MusterMine(
        project=services().project(),
        fan_out=True,
        tasks=components.working(),
        bound=components.bound,
        attended=attended() and components.attended,
        batch=components.batch,
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
    "heal_mine",
    "job_gate",
    "land_answers",
    "land_job",
    "mend_job",
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
