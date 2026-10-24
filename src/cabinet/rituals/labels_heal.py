"""Conjuration: ``labels.heal`` makes the labels ``heal`` reads and puts on.

    vekna cast labels.heal

The step lives in ``cabinet.gates.ritual.vekna.labels``; this module is the
ritual itself and the surface vekna sweeps.
"""

from vekna.lexicon import NoComponents, ritual

from cabinet.gates.ritual.vekna.labels import conjure
from cabinet.pacts.project import Conjure
from cabinet.pacts.services import services


@ritual("labels.heal")
def labels_heal(_: NoComponents) -> Conjure:
    project = services().project()
    return Conjure(project=project, specs=project.labels.conjured())


__all__ = ["conjure", "labels_heal"]
