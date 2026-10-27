"""Evocation: ``heal.pr`` heals one pull request, in a worktree of its own.

    vekna cast heal.pr --number N [--plan-only true] [--bound N] [--batch N]

The open pull request of yours numbered ``--number``, whatever the cwd stands
on. ``heal.mine`` queues one for each branch it surveys work on, and the daemon
runs each in a pooled worktree, so the branches heal side by side and your own
checkout never moves. Typed by hand it runs where it was typed, as
``heal.this`` does. The steps live in ``cabinet.gates.ritual.vekna.heal``; this
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
from cabinet.pacts.heal import MusterPr
from cabinet.pacts.healing import HealPr, Run
from cabinet.specs import HEAL_STEPS


# A tree of its own: the cast checks the branch out and commits on it.
@ritual("heal.pr", max_steps=HEAL_STEPS, worktree=True)
def heal_pr(components: HealPr) -> MusterPr:
    return MusterPr(run=mustered(Run, components), number=components.number)


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
