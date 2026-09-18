"""Saying something to a forge's CLI, and making an answer of what came back.

Both adapters drive a command-line client the same way, so the quoting, the
complaint and the raising are one module rather than one per forge. What each
says to its own client is the adapter's business; this is only the asking.
"""

import shlex

from vekna.folio.shell import ShellResult, shell

from cabinet.pacts.forge import ForgeError


def quoted(value: str) -> str:
    return shlex.quote(value)


# Both streams, because a command that dies before it starts says so on
# stderr and nowhere else, and a client that fails silently still has an exit
# code to report.
def _said(result: ShellResult) -> str:
    parts = (result.stdout.strip(), result.stderr.strip())
    return "\n".join(part for part in parts if part) or f"exit code {result.exit_code}"


async def asked(command: str, complaint: str) -> str:
    result = await shell(command, stream=False)
    if result.exit_code:
        msg = f"{complaint}: {_said(result)}"
        raise ForgeError(msg)
    return result.stdout
