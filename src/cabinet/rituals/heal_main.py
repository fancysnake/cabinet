"""Evocation: ``heal.main`` fixes a red base on a branch and opens a pull request.

    vekna cast heal.main [--plan-only true] [--bound N] [--attended false]

Where a configured CI job is red on the base and no fix of yours is open, a
branch named by ``main_fix_branch`` is cut from the base, each red job is fixed
the way the ci task fixes one, and the branch is pushed and opened as a pull
request for ``heal.mine`` to tend. Nothing is pushed to the base and nothing is
merged. The steps live in ``cabinet.gates.ritual.vekna.heal``; this module is
the ritual itself and the surface vekna sweeps.
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
    muster_main,
    muster_mine,
    muster_pr,
    muster_this,
    mustered,
    open_pull,
    pick_job,
    post_answers,
    post_guide,
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
from cabinet.pacts.heal import MusterMain
from cabinet.pacts.healing import Heal
from cabinet.specs import HEAL_STEPS


# A tree of its own: the cast cuts a branch and commits on it.
@ritual("heal.main", max_steps=HEAL_STEPS, worktree=True)
def heal_main(components: Heal) -> MusterMain:
    return mustered(MusterMain, components, "ci")


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
    "heal_main",
    "job_gate",
    "land_answers",
    "land_job",
    "mend_job",
    "merge_base",
    "muster_main",
    "muster_mine",
    "muster_pr",
    "muster_this",
    "open_pull",
    "pick_job",
    "post_answers",
    "post_guide",
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
