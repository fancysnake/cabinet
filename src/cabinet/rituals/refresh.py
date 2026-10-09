"""Transmutation: ``refresh`` merges the base in and makes the gate green.

    vekna cast refresh [--bound N] [--attended true]

The way *Purify Food and Drink* leaves what was there, only fit to use. The
steps are the sweep's, in ``cabinet.gates.ritual.vekna.sweep``, shared with
``cover``; this module is the ritual itself and the surface vekna sweeps.
vekna registers a step when it is decorated, so importing the sweep is what
puts its graph in place; every step is exported, the same list ``cover``
carries, so the facade names the whole graph it casts.
"""

from vekna.lexicon import ritual

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
from cabinet.pacts.pulls import Sweep
from cabinet.pacts.services import services
from cabinet.pacts.sweep import ListPrs
from cabinet.specs import SWEEP_STEPS


# Merge the base in, make the gate green, push, review.
@ritual("refresh", max_steps=SWEEP_STEPS)
def refresh(components: Sweep) -> ListPrs:
    return ListPrs(
        project=services().project(),
        bound=components.bound,
        mode="refresh",
        attended=components.attended,
    )


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
