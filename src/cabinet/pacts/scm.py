"""The worktree and the remote: what git is asked to do."""

from typing import Protocol

from vekna.lexicon import RitualError

from cabinet.pacts.tasks import Ran


# Git said no. The message names what was asked and what git said.
class ScmError(RitualError):
    pass


class ScmProtocol(Protocol):
    # The remote is https and the forge CLI is its credential helper. Asked
    # before the first fetch, because an ssh remote would ask for a passphrase
    # on a terminal no command under a cast has.
    async def preflight(self) -> None: ...

    # Porcelain status: empty is a clean worktree.
    async def status(self) -> str: ...

    # Where the worktree stands, which is not always the branch a step is
    # working on.
    async def here(self) -> str: ...

    async def checkout(self, branch: str) -> None: ...

    # Fetch, stand on the base, and fast-forward it to the remote.
    async def sync_base(self, base: str) -> None: ...

    # Fast-forward the branch to the remote — never reset: a branch a ritual
    # worked on last night carries commits the remote has not seen.
    async def catch_up(self, branch: str) -> None: ...

    # Whether the base is already contained in HEAD, asked before a merge
    # rather than read off git's prose afterwards.
    async def contains(self, base: str) -> bool: ...

    # A merge that failed is not always a conflict, so what git said rides
    # along for the step that reads the index.
    async def merge(self, base: str) -> Ran: ...

    async def unmerged(self) -> list[str]: ...

    # Finish a merge an agent left staged, where one is still open.
    async def continue_merge(self) -> None: ...

    # Stage everything and commit it, a no-op when there is nothing to commit.
    async def commit(self, message: str) -> None: ...

    async def push(self, branch: str) -> None: ...

    # Abort any open merge and stash whatever is dirty. The stash's name where
    # one was made, empty otherwise: a note naming a stash that is not there
    # is a lie.
    async def release(self, branch: str) -> str: ...

    # Commits the remote has not got, or None where git could not say.
    async def ahead(self, branch: str) -> int | None: ...
