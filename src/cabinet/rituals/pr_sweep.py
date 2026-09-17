"""The night's two passes over your open pull requests.

Transmutation — ``pr_refresh``: merges the base in and makes the gate green,
the way *Purify Food and Drink* leaves what was there, only fit to use.

Abjuration — ``pr_cover``: builds the defences up, writing the tests for what
a branch left uncovered.

The steps live in ``cabinet.gates.ritual.vekna.pr_sweep``; this module is the
surface vekna sweeps, and the one place the services are wired.
"""

from cabinet.gates.ritual.vekna.pr_sweep import (
    check_ci,
    check_clean,
    cover,
    finish_merge,
    finish_pr,
    gate_check,
    list_prs,
    merge_base,
    next_pr,
    pr_cover,
    pr_refresh,
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

wire()

__all__ = [
    "check_ci",
    "check_clean",
    "cover",
    "finish_merge",
    "finish_pr",
    "gate_check",
    "list_prs",
    "merge_base",
    "next_pr",
    "pr_cover",
    "pr_refresh",
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
