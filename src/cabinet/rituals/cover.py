"""Abjuration: ``cover`` builds the defences up.

    vekna cast cover [--bound N] [--attended true]

It writes the tests for what a branch left uncovered, where CI says the
coverage or the suite is unhappy. A project without a coverage task leaves
this facade out of its ``.vekna.toml`` and casts ``refresh`` alone.

The steps are the sweep's, in ``cabinet.gates.ritual.vekna.sweep``, shared
with ``refresh``; this module is the ritual itself and the surface vekna
sweeps. Every step of the sweep is exported, not only the ones this ritual
walks, so the graph ``vekna rituals show`` draws is whole whichever facades a
project loads.
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
from cabinet.inits.services import wire
from cabinet.pacts.pulls import Run, Sweep
from cabinet.pacts.services import services

wire()

# The same backstop `refresh` has: the walk is the same length, the loops
# the same shape.
_MAX_STEPS = 240


# Where CI is unhappy about coverage or tests, close the gap.
@ritual("cover", max_steps=_MAX_STEPS)
def cover(components: Sweep) -> Transition:
    run = Run(
        project=services().project(),
        bound=components.bound,
        mode="cover",
        attended=components.attended,
    )
    return goto(list_prs, run)


__all__ = [
    "check_ci",
    "check_clean",
    "close_gap",
    "cover",
    "finish_merge",
    "finish_pr",
    "gate_check",
    "list_prs",
    "merge_base",
    "next_pr",
    "push_work",
    "quality_review",
    "report",
    "resolve_conflicts",
    "set_aside",
    "skip_pr",
    "stand_down",
    "sync_branch",
    "take_pass",
]
