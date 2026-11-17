"""Divination: ``review`` posts the quality review on your pull request.

    vekna cast review [--plan-only true] [--attended false]

``heal.this`` that works the review task and no other. A pull request wearing
the reviewed label has had its review; take the label off to ask again. The
steps live in ``cabinet.gates.ritual.vekna.heal``; this module is the ritual
itself and the surface vekna sweeps.
"""

from vekna.lexicon import ritual

from cabinet.gates.ritual.vekna import heal as steps
from cabinet.pacts.heal import MusterThis
from cabinet.pacts.healing import Heal
from cabinet.specs import HEAL_STEPS


@ritual("review", max_steps=HEAL_STEPS)
def review(components: Heal) -> MusterThis:
    return steps.mustered(MusterThis, components, "review")


__all__ = ["review", "steps"]
