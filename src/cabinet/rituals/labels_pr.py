"""Conjuration: ``labels:pr`` makes the labels the pull request rituals wear.

    vekna cast labels:pr

The step lives in ``cabinet.gates.ritual.vekna.labels``; this module is the
ritual itself and the surface vekna sweeps.
"""

from vekna.lexicon import NoComponents, ritual

from cabinet.gates.ritual.vekna.labels import conjure
from cabinet.pacts.project import Conjure
from cabinet.pacts.services import services


@ritual("labels:pr")
def labels_pr(_: NoComponents) -> Conjure:
    project = services().project()
    return Conjure(project=project, specs=project.labels.conjured())


__all__ = ["conjure", "labels_pr"]
