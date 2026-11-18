"""Divination: ``guide`` posts the smoke-test guide on your pull request.

    vekna cast guide [--plan-only true] [--attended false]

``heal.this`` that works the guide task and no other, the way *Guidance* lends
the one who checks a hand. Only a branch with nothing else to do gets a guide,
and one wearing the qa label has had it; take the label off to ask again. The
steps live in ``cabinet.gates.ritual.vekna.heal``; this module is the ritual
itself and the surface vekna sweeps.
"""

from vekna.lexicon import ritual

from cabinet.gates.ritual.vekna.heal import mustered
from cabinet.pacts.heal import MusterThis
from cabinet.pacts.healing import Heal
from cabinet.specs import HEAL_STEPS


@ritual("guide", max_steps=HEAL_STEPS)
def guide(components: Heal) -> MusterThis:
    return mustered(MusterThis, components, "guide")


__all__ = ["guide"]
