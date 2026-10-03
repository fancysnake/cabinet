"""Asking an agent, and how much it is allowed to touch."""

from typing import Literal, Protocol, TypeVar

from pydantic import BaseModel

# What an agent is meant to do. Every role has a shell and none runs what
# `Project.forbidden()` names: the long tasks, a commit, a push, the forge.
# A `reader` is not given the edit tools, and is not read-only either: its
# shell writes. A `writer` edits.
Role = Literal["reader", "writer"]


# The agent died mid-flight — a spent token budget, a killed CLI. This ends the
# run, but the report is owed first, so it comes back as a value.
class Fallen(BaseModel):
    reason: str


# The agent answered, but not in the shape asked. One branch's problem and not
# the night's: the CLI is alive, and the next pull request starts with every
# chance of going fine.
class Misread(BaseModel):
    reason: str


_OutputT = TypeVar("_OutputT", bound=BaseModel)


class AgentProtocol(Protocol):
    # Nothing reads what the agent said back: the call is judged by what it
    # left in the worktree. A key joins the call to a thread, so a retry meets
    # an agent that remembers the attempt that just failed. `attended` says
    # somebody is at the terminal to be asked; the deny list holds either way.
    async def ask(
        self, prompt: str, *, role: Role, key: str | None = None, attended: bool = False
    ) -> Fallen | None: ...

    async def ask_for(
        self,
        prompt: str,
        *,
        output: type[_OutputT],
        role: Role,
        key: str | None = None,
        attended: bool = False,
    ) -> _OutputT | Fallen | Misread: ...
