"""Make the labels the other rituals read and write.

    vekna cast labels
    vekna cast labels.pr
    vekna cast labels.identify

One call per label, created where it is missing and refreshed where it is
there, so casting it twice is as safe as once. Which labels is the ritual's
say: `labels.pr` hands over what the pull request rituals wear,
`labels.identify` what `identify` puts on issues, and `labels` both. Cast
`labels` once to set a project up; `labels.pr` again after changing
`[cabinet.labels]`.
"""

from vekna.lexicon import Done, RitualError, step

from cabinet.pacts.forge import ForgeError
from cabinet.pacts.project import Conjure, Labelled
from cabinet.pacts.services import services


# Create every label, or bring it up to date.
@step
async def conjure(wanted: Conjure) -> Done[Labelled]:
    forge = services().forge(wanted.project)
    try:
        for spec in wanted.specs:
            await forge.ensure_label(spec)
    except ForgeError as error:
        raise RitualError(str(error)) from error
    return Done(Labelled(names=[spec.name for spec in wanted.specs]))
