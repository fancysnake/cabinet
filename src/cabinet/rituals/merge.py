"""Transmutation: ``merge`` brings the base into your branch, gate green.

    vekna cast merge [--plan-only true] [--bound N] [--attended false]

``heal.this`` that works the merge task and no other, the way *Mending* joins
what was split. Only a conflict makes a merge todo, so a branch that is merely
behind is left as it is. The steps live in ``cabinet.gates.ritual.vekna.heal``;
this module is the ritual itself and the surface vekna sweeps.
"""

from vekna.lexicon import ritual

from cabinet.gates.ritual.vekna import heal as steps
from cabinet.pacts.heal import MusterThis
from cabinet.pacts.healing import Heal
from cabinet.specs import HEAL_STEPS


@ritual("merge", max_steps=HEAL_STEPS)
def merge(components: Heal) -> MusterThis:
    return steps.mustered(MusterThis, components, "merge")


__all__ = ["merge", "steps"]
