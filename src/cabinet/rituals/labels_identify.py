"""Conjuration: ``labels.identify`` makes the labels ``identify`` puts on issues.

    vekna cast labels.identify

The step lives in ``cabinet.gates.ritual.vekna.labels``; this module is the
ritual itself and the surface vekna sweeps.
"""

from vekna.lexicon import NoComponents, ritual

from cabinet.gates.ritual.vekna.labels import conjure
from cabinet.pacts.issues import ISSUE_LABELS
from cabinet.pacts.project import Conjure
from cabinet.pacts.services import services


@ritual("labels.identify")
def labels_identify(_: NoComponents) -> Conjure:
    return Conjure(project=services().project(), specs=ISSUE_LABELS)


__all__ = ["conjure", "labels_identify"]
