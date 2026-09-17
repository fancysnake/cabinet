"""Asking an agent, and how much it is allowed to touch."""

from typing import Literal, Protocol

from pydantic import BaseModel

# What an agent may reach. `reader` sees the code and read-only git. `writer`
# edits files and runs what the project's `may_run` allows. `resolver` may also
# stage, because staging is the only thing the ritual reads to know a conflict
# is gone. None of them commits, pushes, or speaks to the forge.
Role = Literal["reader", "writer", "resolver"]


# The agent died mid-flight — a spent token budget, a killed CLI. This ends the
# run, but the report is owed first, so it comes back as a value.
class Fallen(BaseModel):
    reason: str


# The agent answered, but not in the shape asked. One branch's problem and not
# the night's: the CLI is alive, and the next pull request starts with every
# chance of going fine.
class Misread(BaseModel):
    reason: str


class AgentProtocol(Protocol):
    # Nothing reads what the agent said back: the call is judged by what it
    # left in the worktree. A key joins the call to a thread, so a retry meets
    # an agent that remembers the attempt that just failed.
    async def ask(
        self, prompt: str, *, role: Role, key: str | None = None
    ) -> Fallen | None: ...

    async def ask_for[OutputT: BaseModel](
        self, prompt: str, *, output: type[OutputT], role: Role, key: str | None = None
    ) -> OutputT | Fallen | Misread: ...
