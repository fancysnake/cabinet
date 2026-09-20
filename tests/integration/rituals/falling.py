"""An agent that dies on every call, bound in place of the real one.

The trial's coding double answers from a script and raises on a call nobody
scripted, which is the test's mistake and not the agent's death — so a dead
agent is a service double at the protocol boundary instead.
"""

from typing import TypeVar

from pydantic import BaseModel
from typing_extensions import override

from cabinet.inits.services import Services
from cabinet.pacts.agent import AgentProtocol, Fallen, Misread, Role
from cabinet.pacts.project import Project
from cabinet.pacts.services import bind

_OutputT = TypeVar("_OutputT", bound=BaseModel)


class FallingAgent(AgentProtocol):
    @override
    async def ask(
        self, prompt: str, *, role: Role, key: str | None = None, attended: bool = False
    ) -> Fallen | None:
        return Fallen(reason="the agent stopped mid-flight: boom")

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
        return Fallen(reason="the agent stopped mid-flight: boom")


class _Falling(Services):
    @override
    def agent(self, project: Project) -> AgentProtocol:
        return FallingAgent()


def falling() -> None:
    bind(_Falling())
