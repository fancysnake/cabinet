"""Evocation: ``heal.this`` takes your branch's pull request as far as it goes.

    vekna cast heal.this [--plan-only true] [--bound N] [--batch N]

The pull request of the branch at the cwd. The steps live in
``cabinet.gates.ritual.vekna.heal``, shared with ``heal.mine`` and the task
rituals; this module is the ritual itself and the surface vekna sweeps.
"""

from vekna.lexicon import ritual

from cabinet.gates.ritual.vekna.heal.cast import mustered
from cabinet.pacts.heal import MusterThis
from cabinet.pacts.healing import Heal
from cabinet.specs import HEAL_STEPS


@ritual("heal.this", max_steps=HEAL_STEPS)
def heal_this(components: Heal) -> MusterThis:
    return mustered(MusterThis, components)


__all__ = ["heal_this"]
