"""Asking Claude, with the reach each role is allowed and nothing more.

Unattended, every call runs under `dontAsk`: a tool outside the allowlist is refused
silently, so an unattended cast never hangs on a prompt and an agent never
commits, pushes, runs a sweep, or speaks to the forge — whatever the prompt
says. Attended, the mode is `auto`: the allowlist still approves what it names,
and what is outside it is judged, with somebody there to be asked. The list is
built from the same project setting the prompt quotes.
"""

import logging
from collections.abc import Awaitable, Callable
from typing import TypeVar

from claude_agent_sdk import ClaudeSDKError
from pydantic import BaseModel
from typing_extensions import override
from vekna.folio.coding import CodingOpts, CodingOutputError, Session, coding
from vekna.folio.coding_claude import ClaudeOptions
from vekna.lexicon import RitualError

from cabinet.pacts.agent import AgentProtocol, Fallen, Misread, Role
from cabinet.pacts.project import Project

_LOG = logging.getLogger(__name__)
AnsweredT = TypeVar("AnsweredT")
_OutputT = TypeVar("_OutputT", bound=BaseModel)

# Read-only git: enough to see what the branch changed and why.
_READER = [
    "Read",
    "Grep",
    "Glob",
    "Bash(git diff:*)",
    "Bash(git log:*)",
    "Bash(git show:*)",
    "Bash(git status:*)",
    "Bash(git blame:*)",
]
_WRITER = ["Edit", "Write", "MultiEdit"]
# Staging is the only thing the ritual reads to know a conflict is gone.
_RESOLVER = ["Bash(git add:*)"]


def allowed_tools(role: Role, project: Project) -> list[str]:
    tools = list(_READER)
    if role == "reader":
        return tools
    tools += _WRITER
    tools += [f"Bash({prefix}:*)" for prefix in project.agent.may_run]
    if role == "resolver":
        tools += _RESOLVER
    return tools


# A key is what makes a call a continuation: the same key twice is an agent
# that remembers writing the first answer.
def _session(key: str | None) -> Session:
    return Session.CONTINUE if key is not None else Session.NEW


# Both failure policies, in one place: the two calls below it are the same
# call with and without a shape, and answering one death differently
# depending on which a step reached for is how a night ends two ways.
# Caught here and nowhere else, because an agent dying mid-flight has to end
# the run but the report is owed first, and an exception leaving a step takes
# the report with it — so the failure comes back as a value.
# `CodingOutputError` is a `RitualError`, so it is caught ahead of the rest or
# not at all, and it is answered differently: an agent whose JSON does not fit
# the schema is a bad answer, not a dead CLI, and ending the whole night over
# one would cost every pull request behind this one.
async def _guarded(
    call: Callable[[], Awaitable[AnsweredT]],
) -> AnsweredT | Fallen | Misread:
    try:
        return await call()
    except CodingOutputError as error:
        return Misread(reason=f"the agent did not answer in the shape asked: {error}")
    except (ClaudeSDKError, RitualError, OSError) as error:
        _LOG.exception("the agent stopped mid-flight")
        return Fallen(reason=f"the agent stopped mid-flight: {error}")


class ClaudeAgent(AgentProtocol):
    def __init__(self, project: Project) -> None:
        self._project = project

    def _opts(self, role: Role, *, attended: bool) -> CodingOpts:
        agent = self._project.agent
        return CodingOpts(
            model=agent.model,
            focus_options=ClaudeOptions(
                permission_mode="auto" if attended else "dontAsk",
                allowed_tools=allowed_tools(role, self._project),
                effort=agent.effort,
                max_turns=agent.max_turns or None,
            ),
        )

    @override
    async def ask(
        self, prompt: str, *, role: Role, key: str | None = None, attended: bool = False
    ) -> Fallen | None:
        answered = await _guarded(
            lambda: coding(
                prompt,
                opts=self._opts(role, attended=attended),
                session=_session(key),
                key=key,
            )
        )
        # Nothing was asked for in a shape, so there is no shape to misread:
        # what a caller of this one wants to know is whether the agent died.
        return answered if isinstance(answered, Fallen) else None

    @override
    async def ask_for(
        self,
        prompt: str,
        *,
        output: type[_OutputT],
        role: Role,
        key: str | None = None,
        attended: bool = False,
    ) -> _OutputT | Fallen | Misread:
        return await _guarded(
            lambda: coding(
                prompt,
                output=output,
                opts=self._opts(role, attended=attended),
                session=_session(key),
                key=key,
            )
        )
