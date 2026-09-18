"""Transmutation: ``refresh`` merges the base in and makes the gate green.

    vekna cast refresh [--bound N] [--attended true]

The way *Purify Food and Drink* leaves what was there, only fit to use. The
steps are the sweep's, in ``cabinet.gates.ritual.vekna.sweep``, shared with
``cover``; this module is the ritual itself and the surface vekna sweeps.
Every step of the sweep is exported, not only the ones this ritual walks, so
the graph ``vekna rituals show`` draws is whole whichever facades a project
loads. That list is the same list ``cover`` carries, and it stays copied
rather than shared: vekna registers what it finds in the namespace of the
module a project names, so a project naming this facade alone would get a
graph that stops at the first step of a module it did not name.
"""

from vekna.lexicon import Transition, goto, ritual

from cabinet.gates.ritual.vekna.sweep import (
    check_ci,
    check_clean,
    close_gap,
    finish_merge,
    finish_pr,
    gate_check,
    list_prs,
    merge_base,
    next_pr,
    push_work,
    quality_review,
    report,
    resolve_conflicts,
    set_aside,
    skip_pr,
    stand_down,
    sync_branch,
    take_pass,
)
from cabinet.pacts.pulls import Run, Sweep
from cabinet.pacts.services import services

# The backstop, not the control — the per-step bounds are. Six pull requests
# through ~9 steps each, with three repair loops that may each burn two turns
# per `--bound`, comes to a little over 200 at the maximum bound; this sits
# above that, because tripping it costs the report as well as the run.
_MAX_STEPS = 240


# Merge the base in, make the gate green, push, review.
@ritual("refresh", max_steps=_MAX_STEPS)
def refresh(components: Sweep) -> Transition:
    run = Run(
        project=services().project(),
        bound=components.bound,
        mode="refresh",
        attended=components.attended,
    )
    return goto(list_prs, run)


__all__ = [
    "check_ci",
    "check_clean",
    "close_gap",
    "finish_merge",
    "finish_pr",
    "gate_check",
    "list_prs",
    "merge_base",
    "next_pr",
    "push_work",
    "quality_review",
    "refresh",
    "report",
    "resolve_conflicts",
    "set_aside",
    "skip_pr",
    "stand_down",
    "sync_branch",
    "take_pass",
]
