"""Saying something to a forge's CLI, and making an answer of what came back.

Both adapters drive a command-line client the same way, so the quoting, the
complaint and the raising are one module rather than one per forge. What each
says to its own client is the adapter's business; this is only the asking.
"""

import re
import shlex

from vekna.folio.shell import ShellResult, shell

from cabinet.pacts.forge import ForgeError, ForgeLimitedError

_LIMITED = re.compile(
    r"rate limit|abuse detection|too many requests", flags=re.IGNORECASE
)

# Seconds, fifteen minutes and a bit between them. A primary limit can take an
# hour to clear, so a longer spell ends the cast instead.
_PAUSES = (15, 30, 60, 120, 240, 480)


def quoted(value: str) -> str:
    return shlex.quote(value)


# Both streams, because a command that dies before it starts says so on
# stderr and nowhere else, and a client that fails silently still has an exit
# code to report.
def _said(result: ShellResult) -> str:
    parts = (result.stdout.strip(), result.stderr.strip())
    return "\n".join(part for part in parts if part) or f"exit code {result.exit_code}"


# Stderr only: stdout of a failed call is the response body, which can quote
# anything.
def _limited(result: ShellResult) -> bool:
    return bool(result.exit_code and _LIMITED.search(result.stderr))


# The pause is a shell rite so a resumed cast replays it off the journal
# instead of sitting through it again. The answer comes back as it is, refusal
# included, for callers that read a refusal themselves; only a limit that
# outlasts every pause raises.
async def tried(command: str) -> ShellResult:
    result = await shell(command, stream=False)
    for pause in _PAUSES:
        if not _limited(result):
            return result
        await shell(f"sleep {pause}", stream=False)
        result = await shell(command, stream=False)
    if _limited(result):
        msg = f"still rate limited after {sum(_PAUSES) // 60} minutes: {_said(result)}"
        raise ForgeLimitedError(msg)
    return result


async def asked(command: str, complaint: str) -> str:
    result = await tried(command)
    if result.exit_code:
        msg = f"{complaint}: {_said(result)}"
        raise ForgeError(msg)
    return result.stdout
