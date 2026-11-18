"""Abjuration: ``ci`` makes your branch's red CI jobs green.

    vekna cast ci [--plan-only true] [--bound N]

``heal.this`` that works the ci task and no other, the way *Lesser
Restoration* ends one condition at a time. Only a red check on a job in
``[cabinet.ci.jobs]`` makes a ci todo. The steps live in
``cabinet.gates.ritual.vekna.heal``; this module is the ritual itself and the
surface vekna sweeps.
"""

from vekna.lexicon import ritual

from cabinet.gates.ritual.vekna.heal import mustered
from cabinet.pacts.heal import MusterThis
from cabinet.pacts.healing import Heal
from cabinet.specs import HEAL_STEPS


@ritual("ci", max_steps=HEAL_STEPS)
def ci(components: Heal) -> MusterThis:
    return mustered(MusterThis, components, "ci")


__all__ = ["ci"]
