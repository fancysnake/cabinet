"""Conjuration: ``labels`` brings the labels the other rituals need into being.

    vekna cast labels

The step lives in ``cabinet.gates.ritual.vekna.labels``; this module is the
ritual itself and the surface vekna sweeps.
"""

from vekna.lexicon import NoComponents, Transition, goto, ritual

from cabinet.gates.ritual.vekna.labels import conjure
from cabinet.inits.services import wire
from cabinet.pacts.services import services

wire()


@ritual("labels")
def labels(_: NoComponents) -> Transition:
    return goto(conjure, services().project())


__all__ = ["conjure", "labels"]
