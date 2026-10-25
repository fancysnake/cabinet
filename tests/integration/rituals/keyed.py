"""An agent that writes down the session key of every call, bound in place.

A session continues only within one cast, and a test walks one step at a time,
so which calls share a session is read off the keys instead.
"""

from typing import TypeVar

from pydantic import BaseModel
from typing_extensions import override

from cabinet.inits.services import Services
from cabinet.pacts.agent import AgentProtocol, Fallen, Misread, Role
from cabinet.pacts.project import Project
from cabinet.pacts.services import bind

_OutputT = TypeVar("_OutputT", bound=BaseModel)


class KeyedAgent(AgentProtocol):
    def __init__(self, keys: list[str | None]) -> None:
        self._keys = keys

    @override
    async def ask(
        self, prompt: str, *, role: Role, key: str | None = None, attended: bool = False
    ) -> Fallen | None:
        self._keys.append(key)
        return None

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
        self._keys.append(key)
        return Misread(reason="a keyed agent answers nothing")


class _Keyed(Services):
    def __init__(self, keys: list[str | None]) -> None:
        super().__init__()
        self._keys = keys

    @override
    def agent(self, project: Project) -> AgentProtocol:
        return KeyedAgent(self._keys)


# The list every call's key lands in, in order.
def keyed() -> list[str | None]:
    keys: list[str | None] = []
    bind(_Keyed(keys))
    return keys
