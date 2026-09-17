"""Asking Claude, with the reach each role is allowed and nothing more.

Unattended, every call runs under `dontAsk`: a tool outside the allowlist is refused
silently, so an unattended cast never hangs on a prompt and an agent never
commits, pushes, runs a sweep, or speaks to the forge — whatever the prompt
says. Attended, the mode is `auto`: the allowlist still approves what it names,
and what is outside it is judged, with somebody there to be asked. The list is
built from the same project setting the prompt quotes.
"""

import logging
from typing import TYPE_CHECKING, override

from claude_agent_sdk import ClaudeSDKError
from pydantic import BaseModel
from vekna.folio.coding import CodingOpts, CodingOutputError, Session, coding
from vekna.folio.coding_claude import ClaudeOptions
from vekna.lexicon import RitualError

from cabinet.pacts.agent import AgentProtocol, Fallen, Misread, Role

if TYPE_CHECKING:
    from cabinet.pacts.project import Project

_LOG = logging.getLogger(__name__)

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

    # Caught here and nowhere else: an agent dying mid-flight has to end the
    # run, but the report is owed first, and an exception leaving a step
    # takes the report with it. So the failure comes back as a value.
    @override
    async def ask(
        self, prompt: str, *, role: Role, key: str | None = None, attended: bool = False
    ) -> Fallen | None:
        session = Session.CONTINUE if key is not None else Session.NEW
        try:
            opts = self._opts(role, attended=attended)
            await coding(prompt, opts=opts, session=session, key=key)
        except (ClaudeSDKError, RitualError, OSError) as error:
            _LOG.exception("the agent stopped mid-flight")
            return Fallen(reason=f"the agent stopped mid-flight: {error}")
        return None

    @override
    async def ask_for[OutputT: BaseModel](
        self,
        prompt: str,
        *,
        output: type[OutputT],
        role: Role,
        key: str | None = None,
        attended: bool = False,
    ) -> OutputT | Fallen | Misread:
        session = Session.CONTINUE if key is not None else Session.NEW
        try:
            return await coding(
                prompt,
                output=output,
                opts=self._opts(role, attended=attended),
                session=session,
                key=key,
            )
        # Caught ahead of the rest and answered differently: an agent whose
        # JSON does not fit the schema is a bad answer, not a dead CLI, and
        # ending the whole night over one would cost every pull request
        # behind this one.
        except CodingOutputError as error:
            return Misread(
                reason=f"the agent did not answer in the shape asked: {error}"
            )
        except (ClaudeSDKError, RitualError, OSError) as error:
            _LOG.exception("the agent stopped mid-flight")
            return Fallen(reason=f"the agent stopped mid-flight: {error}")
