"""Conjuration: ``labels`` makes every label cabinet's rituals use.

    vekna cast labels

The full setup: what ``labels.heal`` and ``labels.identify`` each make, in one
cast. The step lives in ``cabinet.gates.ritual.vekna.labels``; this module is
the ritual itself and the surface vekna sweeps.
"""

from vekna.lexicon import NoComponents, ritual

from cabinet.pacts.issues import ISSUE_LABELS
from cabinet.pacts.project import LABELS_NEEDS, Conjure
from cabinet.pacts.services import services


@ritual("labels")
def labels(_: NoComponents) -> Conjure:
    project = services().project(LABELS_NEEDS)
    return Conjure(project=project, specs=[*project.labels.conjured(), *ISSUE_LABELS])


__all__ = ["labels"]
