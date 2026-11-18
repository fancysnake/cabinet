"""Enchantment: ``answer`` settles the review threads on your branch with you.

    vekna cast answer [--plan-only true] [--bound N] [--batch N]

``heal.this`` that works the answer task and no other, the way *Command* puts
one word to each listener. Only an unresolved review thread makes an answer
todo, and only an attended cast works it: unattended, the report says how many
threads wait. The steps live in ``cabinet.gates.ritual.vekna.heal``; this
module is the ritual itself and the surface vekna sweeps.
"""

from vekna.lexicon import ritual

from cabinet.gates.ritual.vekna.heal import mustered
from cabinet.pacts.heal import MusterThis
from cabinet.pacts.healing import Heal
from cabinet.specs import HEAL_STEPS


@ritual("answer", max_steps=HEAL_STEPS)
def answer(components: Heal) -> MusterThis:
    return mustered(MusterThis, components, "answer")


__all__ = ["answer"]
