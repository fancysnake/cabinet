"""Make the labels the other rituals read and write.

    vekna cast labels

One call per label, created where it is missing and refreshed where it is
there, so casting it twice is as safe as once. Cast it on a repository before
the first sweep, and again after changing `[cabinet.labels]`.
"""

from vekna.lexicon import Done, RitualError, step

from cabinet.pacts.forge import ForgeError
from cabinet.pacts.project import Conjure, Labelled
from cabinet.pacts.services import services


# Create every label, or bring it up to date.
@step
async def conjure(conjuring: Conjure) -> Done[Labelled]:
    project = conjuring.project
    forge = services().forge(project)
    wanted = project.labels.conjured()
    try:
        for spec in wanted:
            await forge.ensure_label(spec)
    except ForgeError as error:
        raise RitualError(str(error)) from error
    return Done(Labelled(names=[spec.name for spec in wanted]))
