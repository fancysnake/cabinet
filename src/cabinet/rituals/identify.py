"""Divination: ``identify`` types and sizes your open issues.

    vekna cast identify [--batch N]

A page at a time, unasked. The steps live in
``cabinet.gates.ritual.vekna.identify``; this module is the ritual itself and the
surface vekna sweeps.
"""

from vekna.lexicon import ritual

from cabinet.gates.ritual.vekna.identify import gather, identify_page, leaf, pin, tally
from cabinet.pacts.identify import Gather
from cabinet.pacts.issues import Identify
from cabinet.pacts.services import services


@ritual("identify")
def identify(components: Identify) -> Gather:
    return Gather(project=services().project(), batch=components.batch)


__all__ = ["gather", "identify", "identify_page", "leaf", "pin", "tally"]
