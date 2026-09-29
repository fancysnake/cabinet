"""Conjuration: ``labels:issue`` makes the labels ``refine`` puts on issues.

    vekna cast labels:issue

The step lives in ``cabinet.gates.ritual.vekna.labels``; this module is the
ritual itself and the surface vekna sweeps.
"""

from vekna.lexicon import NoComponents, Transition, goto, ritual

from cabinet.gates.ritual.vekna.labels import conjure
from cabinet.pacts.project import ISSUE_LABELS, Conjuring
from cabinet.pacts.services import services


@ritual("labels:issue")
def labels_issue(_: NoComponents) -> Transition:
    return goto(conjure, Conjuring(project=services().project(), specs=ISSUE_LABELS))


__all__ = ["conjure", "labels_issue"]
