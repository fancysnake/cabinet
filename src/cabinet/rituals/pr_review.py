"""Divination: ``pr_review`` reads what the reviews found.

With you at the terminal, it answers every thread and ships the branch.

The steps live in ``cabinet.gates.ritual.vekna.pr_review``; this module is the
surface vekna sweeps, and the one place the services are wired.
"""

from cabinet.gates.ritual.vekna.pr_review import (
    answer,
    gates,
    land,
    look,
    pick,
    plan,
    pr_review,
    queue_up,
    recap,
    settle,
    work,
)
from cabinet.inits.services import wire

wire()

__all__ = [
    "answer",
    "gates",
    "land",
    "look",
    "pick",
    "plan",
    "pr_review",
    "queue_up",
    "recap",
    "settle",
    "work",
]
