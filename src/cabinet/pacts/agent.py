"""Asking an agent, and how much it is allowed to touch."""

from typing import Literal, Protocol, TypeVar

from pydantic import BaseModel

# The work a call is doing, which picks its model and its tools. `plan`
# verifies, plans or checks an issue against the code; `build` implements;
# `review` judges a branch; `fix` repairs what came back; `doc` writes from the
# branch.
Job = Literal["plan", "build", "review", "fix", "doc"]


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
    # A job picks the model and the tools. Nothing reads what the agent said
    # back: the call is judged by what it left in the worktree. A key joins the
    # call to a thread, so a retry meets an agent that remembers the attempt
    # that just failed.
    async def ask(
        self, prompt: str, *, job: Job, key: str | None = None
    ) -> Fallen | None: ...

    async def ask_for(
        self, prompt: str, *, output: type[_OutputT], job: Job, key: str | None = None
    ) -> _OutputT | Fallen | Misread: ...
