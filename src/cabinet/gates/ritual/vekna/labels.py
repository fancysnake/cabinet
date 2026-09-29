"""Make the labels the other rituals read and write.

    vekna cast labels:pr
    vekna cast labels:issue

One call per label, created where it is missing and refreshed where it is
there, so casting it twice is as safe as once. Which labels is the ritual's
say: `labels:pr` hands over what the pull request rituals wear, and
`labels:issue` what `refine` puts on issues. Cast `labels:pr` before the
first sweep and again after changing `[cabinet.labels]`; `labels:issue`
before the first `refine`.
"""

from vekna.lexicon import RitualError, Transition, done, step

from cabinet.pacts.forge import ForgeError
from cabinet.pacts.project import Conjuring, Labelled
from cabinet.pacts.services import services


# Create every label, or bring it up to date.
@step
async def conjure(wanted: Conjuring) -> Transition:
    forge = services().forge(wanted.project)
    try:
        for spec in wanted.specs:
            await forge.ensure_label(spec)
    except ForgeError as error:
        raise RitualError(str(error)) from error
    return done(Labelled(names=[spec.name for spec in wanted.specs]))
