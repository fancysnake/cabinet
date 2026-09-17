"""Make the labels the other rituals read and write.

    vekna cast labels

One call per label, created where it is missing and refreshed where it is
there, so casting it twice is as safe as once. Cast it on a repository before
the first sweep, and again after changing `[cabinet.labels]`.
"""

from vekna.lexicon import (
    NoComponents,
    RitualError,
    Transition,
    done,
    goto,
    ritual,
    step,
)

from cabinet.pacts.forge import ForgeError
from cabinet.pacts.project import Labelled, Project
from cabinet.pacts.services import services


@ritual("labels")
def labels(_: NoComponents) -> Transition:
    return goto(conjure, services().project())


# Create every label, or bring it up to date.
@step
async def conjure(project: Project) -> Transition:
    forge = services().forge(project)
    wanted = project.labels.conjured()
    try:
        for spec in wanted:
            await forge.ensure_label(spec)
    except ForgeError as error:
        raise RitualError(str(error)) from error
    return done(Labelled(names=[spec.name for spec in wanted]))
