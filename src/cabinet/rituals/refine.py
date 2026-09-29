"""Divination: ``refine`` types and sizes your open issues.

    vekna cast refine [--batch N]

With you at the terminal, a page at a time. The steps live in
``cabinet.gates.ritual.vekna.refine``; this module is the ritual itself and the
surface vekna sweeps.
"""

from vekna.lexicon import ritual

from cabinet.gates.ritual.vekna.refine import gather, leaf, pin, refine_page, tally
from cabinet.pacts.issues import Refine
from cabinet.pacts.refine import Gather
from cabinet.pacts.services import services


@ritual("refine")
def refine(components: Refine) -> Gather:
    return Gather(project=services().project(), batch=components.batch)


__all__ = ["gather", "leaf", "pin", "refine", "refine_page", "tally"]
