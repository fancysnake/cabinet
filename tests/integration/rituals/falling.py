"""An agent that dies on every call, bound in place of the real one.

The trial's coding double answers from a script and raises on a call nobody
scripted, which is the test's mistake and not the agent's death — so a dead
agent is a service double at the protocol boundary instead.
"""

from typing import TYPE_CHECKING, override

from pydantic import BaseModel

from cabinet.inits.services import Services
from cabinet.pacts.agent import AgentProtocol, Fallen, Misread, Role
from cabinet.pacts.services import bind

if TYPE_CHECKING:
    from cabinet.pacts.project import Project


class FallingAgent(AgentProtocol):
    @override
    async def ask(
        self, prompt: str, *, role: Role, key: str | None = None
    ) -> Fallen | None:
        return Fallen(reason="the agent stopped mid-flight: boom")

    @override
    async def ask_for[OutputT: BaseModel](
        self, prompt: str, *, output: type[OutputT], role: Role, key: str | None = None
    ) -> OutputT | Fallen | Misread:
        return Fallen(reason="the agent stopped mid-flight: boom")


class _Falling(Services):
    @override
    def agent(self, project: Project) -> AgentProtocol:
        return FallingAgent()


def falling() -> None:
    bind(_Falling())
