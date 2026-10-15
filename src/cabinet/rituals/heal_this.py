"""Evocation: ``heal.this`` says what your branch's pull request needs next.

    vekna cast heal.this --plan-only true

Only the survey so far, so only ``--plan-only true`` casts. The steps live in
``cabinet.gates.ritual.vekna.heal``, shared with ``heal.mine``; this module is
the ritual itself and the surface vekna sweeps.
"""

from vekna.lexicon import RitualError, ritual

from cabinet.gates.ritual.vekna.heal import chart, muster_mine, muster_this, survey
from cabinet.pacts.heal import MusterThis
from cabinet.pacts.healing import Heal
from cabinet.pacts.services import services


@ritual("heal.this")
def heal_this(components: Heal) -> MusterThis:
    if not components.plan_only:
        msg = "heal.this only surveys so far: cast it with --plan-only true"
        raise RitualError(msg)
    return MusterThis(project=services().project())


__all__ = ["chart", "heal_this", "muster_mine", "muster_this", "survey"]
