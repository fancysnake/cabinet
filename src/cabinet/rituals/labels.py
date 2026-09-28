"""Conjuration: ``labels`` brings the labels the other rituals need into being.

    vekna cast labels

The step lives in ``cabinet.gates.ritual.vekna.labels``; this module is the
ritual itself and the surface vekna sweeps.
"""

from vekna.lexicon import NoComponents, ritual

from cabinet.gates.ritual.vekna.labels import conjure
from cabinet.pacts.project import Conjure
from cabinet.pacts.services import services


@ritual("labels")
def labels(_: NoComponents) -> Conjure:
    return Conjure(project=services().project())


__all__ = ["conjure", "labels"]
