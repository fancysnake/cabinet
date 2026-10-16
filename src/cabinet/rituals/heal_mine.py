"""Evocation: ``heal.mine`` says what each of your pull requests needs next.

    vekna cast heal.mine --plan-only true

Only the survey so far, so only ``--plan-only true`` casts. The steps live in
``cabinet.gates.ritual.vekna.heal``, shared with ``heal.this``; this module is
the ritual itself and the surface vekna sweeps.
"""

from vekna.lexicon import RitualError, ritual

from cabinet.gates.ritual.vekna.heal import chart, muster_mine, muster_this, survey
from cabinet.pacts.heal import MusterMine
from cabinet.pacts.healing import Heal
from cabinet.pacts.services import services


@ritual("heal.mine")
def heal_mine(components: Heal) -> MusterMine:
    if not components.plan_only:
        msg = "heal.mine only surveys so far: cast it with --plan-only true"
        raise RitualError(msg)
    return MusterMine(project=services().project())


__all__ = ["chart", "heal_mine", "muster_mine", "muster_this", "survey"]
