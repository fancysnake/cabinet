"""The forge: where the pull requests, their threads and their labels live."""

from collections.abc import Sequence
from typing import Protocol

from vekna.lexicon import RitualError

from cabinet.pacts.project import LabelSpec
from cabinet.pacts.pulls import Board, PullRequest
from cabinet.pacts.threads import Finding, Posted, Thread


# The forge would not answer, or answered something unreadable. The message
# says which, in the CLI's own words.
class ForgeError(RitualError):
    pass


class ForgeProtocol(Protocol):
    # Every open pull request of yours, as the forge lists them.
    async def pulls(self) -> list[PullRequest]: ...

    async def labels(self, number: int) -> list[str]: ...

    # Several go on or off in one call rather than one apiece: two labels put
    # on for the same reason should not be able to half-happen.
    async def label(
        self, number: int, *, add: Sequence[str] = (), remove: Sequence[str] = ()
    ) -> None: ...

    # Every review thread, settled or not: the reader skips the settled ones,
    # and a count of the open ones is what says a branch has work.
    async def threads(self, number: int) -> list[Thread]: ...

    async def reply(self, number: int, thread: Thread, body: str) -> None: ...

    async def resolve(self, number: int, thread: Thread) -> None: ...

    # What CI made of the branch as it stands now, not as the listing saw it.
    async def board(self, branch: str) -> Board: ...

    # A whole review in one call, so an adapter resolves what it needs to
    # anchor the items once instead of once per item. Each goes up anchored to
    # its line, or plainly where the forge refuses the anchor: losing the
    # anchor is fine, losing the item is not.
    # The one call here that does not raise: it stops at the first item that
    # will not go up at all and answers how far it got, because what is
    # already posted cannot be taken down again and the caller has to decide
    # about it rather than retry it.
    async def comment(self, number: int, findings: Sequence[Finding]) -> Posted: ...

    # The new issue's URL.
    async def issue(self, title: str, body: str) -> str: ...

    # The label exists with this colour and description afterwards, whether or
    # not it did before.
    async def ensure_label(self, spec: LabelSpec) -> None: ...
