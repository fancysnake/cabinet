"""Running one of the repository's own tasks, and what came back."""

from typing import Protocol

from pydantic import BaseModel


class Ran(BaseModel):
    stdout: str
    stderr: str
    exit_code: int


class TasksProtocol(Protocol):
    # Output is streamed to the window while the task runs, and the result
    # holds the full text. It comes in the tool's log shape rather than its
    # terminal one: what comes back is read by an agent and by the morning
    # report, and a terminal recording is neither.
    async def run(self, task: str) -> Ran: ...
