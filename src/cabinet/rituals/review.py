"""Divination: ``review`` reads what the reviews found.

    vekna cast review [--bound N] [--batch N]

With you at the terminal, it answers every thread and ships the branch. The
steps live in ``cabinet.gates.ritual.vekna.review``; this module is the ritual
itself and the surface vekna sweeps.
"""

from vekna.lexicon import ritual

from cabinet.gates.ritual.vekna.review import (
    answer,
    gates,
    land,
    look,
    pick,
    plan,
    queue_up,
    read,
    recap,
    settle,
    work,
)
from cabinet.pacts.review import QueueUp
from cabinet.pacts.reviews import Review
from cabinet.pacts.services import services
from cabinet.specs import REVIEW_STEPS


@ritual("review", max_steps=REVIEW_STEPS)
def review(components: Review) -> QueueUp:
    return QueueUp(
        project=services().project(), bound=components.bound, batch=components.batch
    )


__all__ = [
    "answer",
    "gates",
    "land",
    "look",
    "pick",
    "plan",
    "queue_up",
    "read",
    "recap",
    "review",
    "settle",
    "work",
]
