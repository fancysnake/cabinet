"""Divination: ``review`` reads what the reviews found.

    vekna cast review [--bound N] [--batch N]

With you at the terminal, it answers every thread and ships the branch. The
steps live in ``cabinet.gates.ritual.vekna.review``; this module is the ritual
itself and the surface vekna sweeps.
"""

from vekna.lexicon import Transition, goto, ritual

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
from cabinet.inits.services import wire
from cabinet.pacts.reviews import Picking, Review
from cabinet.pacts.services import services

wire()

# The engine's backstop and nothing else: the repair loop is bounded by the
# person sitting at it, and the branch loop by how many branches were reviewed
# in the night.
_MAX_STEPS = 400


@ritual("review", max_steps=_MAX_STEPS)
def review(components: Review) -> Transition:
    picking = Picking(
        project=services().project(), bound=components.bound, batch=components.batch
    )
    return goto(queue_up, picking)


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
