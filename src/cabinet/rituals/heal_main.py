"""Evocation: ``heal.main`` fixes a red base on a branch and opens a pull request.

    vekna cast heal.main [--plan-only true] [--bound N]

Where a configured CI job is red on the base and no fix of yours is open, a
branch named by ``main_fix_branch`` is cut from the base, each red job is fixed
the way the ci task fixes one, and the branch is pushed and opened as a pull
request for ``heal.mine`` to tend. Nothing is pushed to the base and nothing is
merged. The steps live in ``cabinet.gates.ritual.vekna.heal``; this module is
the ritual itself and the surface vekna sweeps.
"""

from vekna.lexicon import ritual

from cabinet.gates.ritual.vekna.heal.cast import mustered
from cabinet.pacts.heal import MusterMain
from cabinet.pacts.healing import Heal
from cabinet.specs import HEAL_STEPS


# A tree of its own: the cast cuts a branch and commits on it.
@ritual("heal.main", max_steps=HEAL_STEPS, worktree=True)
def heal_main(components: Heal) -> MusterMain:
    return mustered(MusterMain, components, "ci")


__all__ = ["heal_main"]
