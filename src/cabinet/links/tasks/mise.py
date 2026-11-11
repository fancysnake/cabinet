"""Running the repository's mise tasks."""

from typing_extensions import override
from vekna.folio.shell import shell

from cabinet.pacts.tasks import Ran, TasksProtocol


class MiseTasks(TasksProtocol):
    # `CI=1` puts every tool in the chain into its log shape rather than its
    # terminal one — no colour, no cursor tricks. It changes more than the
    # rendering, and that is worth knowing before a gate's answer is read as
    # the answer you would have got yourself: a test runner under it may retry
    # a failure before it counts, pin its workers, or refuse a focused test.
    # Streamed: a gate runs for minutes, and a hung one looks the same as a
    # slow one unless its lines reach the window. The result holds the same
    # text either way.
    @override
    async def run(self, task: str) -> Ran:
        result = await shell(f"CI=1 {task}")
        return Ran(
            stdout=result.stdout, stderr=result.stderr, exit_code=result.exit_code
        )
