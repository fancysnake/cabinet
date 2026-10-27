"""Evocation: ``heal.mine`` queues a ``heal.pr`` for each pull request with work.

    vekna cast heal.mine [--plan-only true] [--bound N] [--attended false] [--batch N]

Every open pull request of yours not wearing the wait label, oldest-modified
first, is surveyed, and this cast works none of them itself: each one with
work goes to a ``heal.pr`` of its own, queued on the daemon, which runs it in a pooled
worktree beside the others. With no daemon listening it says so and fails.
The steps live in ``cabinet.gates.ritual.vekna.heal``, shared with
``heal.this`` and the task rituals; this module is the ritual itself and the
surface vekna sweeps. Every step is exported, so the facade names the whole
graph it casts, and so is ``heal.pr``: a project loading only this facade
can still run what it queues.
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
    muster_pr,
    muster_this,
    mustered,
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
    tally,
    tend,
)
from cabinet.pacts.heal import MusterMine
from cabinet.pacts.healing import Heal
from cabinet.rituals.heal_pr import heal_pr
from cabinet.specs import HEAL_STEPS


@ritual("heal.mine", max_steps=HEAL_STEPS)
def heal_mine(components: Heal) -> MusterMine:
    return mustered(MusterMine, components)


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
    "heal_pr",
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
    "tally",
    "tend",
]
