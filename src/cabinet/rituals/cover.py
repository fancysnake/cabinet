"""Abjuration: ``cover`` builds the defences up.

    vekna cast cover [--bound N] [--attended true]

It writes the tests for what a branch left uncovered, where CI says the
coverage or the suite is unhappy. A project without a coverage task leaves
this facade out of its ``.vekna.toml`` and casts ``refresh`` alone.

The steps are the sweep's, in ``cabinet.gates.ritual.vekna.sweep``, shared
with ``refresh``; this module is the ritual itself and the surface vekna
sweeps. vekna registers a step when it is decorated, so importing the sweep is
what puts its graph in place; every step is exported, the same list ``refresh``
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


# Where CI is unhappy about coverage or tests, close the gap.
@ritual("cover", max_steps=SWEEP_STEPS)
def cover(components: Sweep) -> ListPrs:
    return ListPrs(
        project=services().project(),
        bound=components.bound,
        mode="cover",
        attended=components.attended,
    )


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
