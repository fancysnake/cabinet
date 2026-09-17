"""Transmutation: ``refresh`` merges the base in and makes the gate green.

The way *Purify Food and Drink* leaves what was there, only fit to use.

The steps live in ``cabinet.gates.ritual.vekna.sweep``; this module is the
surface vekna sweeps, and the one place the services are wired. Every step of
the sweep is exported, not only the ones this ritual walks, so the graph
``vekna rituals show`` draws is whole whichever facades a project loads.
"""

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
    refresh,
    report,
    resolve_conflicts,
    set_aside,
    skip_pr,
    stand_down,
    sync_branch,
    take_pass,
)
from cabinet.inits.services import wire

wire()

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
