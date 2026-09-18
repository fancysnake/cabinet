"""What a task's output is worth handing on, to an agent and to the morning."""

import re
from typing import TYPE_CHECKING, override

from cabinet.pacts.services import VerdictsProtocol
from cabinet.specs import BUDGET, VERDICT_LINES

if TYPE_CHECKING:
    from cabinet.pacts.tasks import Ran

# diff-cover's report is self-delimiting — its own banner, then everything to
# the end of the run — so the one reader of the report needs no budget.
_BANNER = "Diff Coverage"
_MISSING = "Missing lines"

# How mise names the task that failed: the leaf's own name, in the prefix it
# labels that task's output with. A chain stops at the first failure, so the
# first match is the one that broke and anything after it is a parent
# repeating the news.
_FAILED_TASK = re.compile(r"^\[([\w:.-]+)] ERROR task failed", re.MULTILINE)

# Cursor moves and colour. `CI=1` stops most of these being written at all;
# this is for the tools that colour anyway. An escape code is not something
# either reader wants, and in `said` it is budget spent on cursor positions.
_ANSI = re.compile(r"\x1b\[[0-9;?]*[a-zA-Z]")


def _plain(text: str) -> str:
    return _ANSI.sub("", text)


# The budget buys whole lines, and the last line is bought whether it fits or
# not: a tool that pretty-prints a value onto one long line would otherwise
# spend the budget and hand back nothing.
def _tail(text: str) -> str:
    lines = text.splitlines()
    kept: list[str] = []
    left = BUDGET
    for line in reversed(lines):
        left -= len(line) + 1
        if left < 0 and kept:
            break
        kept.append(line)
    if len(kept) == len(lines):
        return "\n".join(lines)
    kept.reverse()
    return "\n".join([f"[{len(lines) - len(kept)} earlier lines omitted]", *kept])


# Timings, counts and timestamps differ on every run, so two runs of the same
# broken suite never match character for character. What is left once the
# digits go is the failing test's name and the tool that named it.
# ponytail: a different failure at the same file and a different line collides
# with this. What that costs is one branch's repair attempts skipped, and the
# report still says what it saw — worth more than a check that never fires.
def same_verdict(one: str, other: str) -> bool:
    return bool(one) and re.sub(r"\d+", "", one) == re.sub(r"\d+", "", other)


class Verdicts(VerdictsProtocol):
    # Both streams: a task that dies before it starts says so on stderr and
    # nowhere else, and an empty complaint is the one thing a repair agent
    # cannot work with. Each stream gets the budget on its own, because mise
    # puts its own task chatter on stderr and the tool's verdict on stdout,
    # and a shared budget is won by whichever stream is longer.
    @override
    def said(self, ran: Ran) -> str:
        return "\n".join(
            _tail(_plain(part)) for part in (ran.stdout, ran.stderr) if part.strip()
        )

    # For the report rather than for an agent, so only one stream: stdout is
    # where every tool in these chains says how it ended, while stderr carries
    # mise's chatter and, under e2e, a web server logging every request.
    # Where stdout said nothing at all, stderr is all there is, and that is
    # the task that died before it started. Blank lines go too: a progress
    # reporter writing over itself leaves hundreds of them.
    @override
    def verdict(self, ran: Ran) -> str:
        spoken = ran.stdout if ran.stdout.strip() else ran.stderr
        lines = [
            stripped
            for line in _plain(spoken).splitlines()
            if (stripped := line.rstrip())
        ]
        return "\n".join(lines[-VERDICT_LINES:])

    # The one task worth re-running while a repair is underway, instead of the
    # whole gate: a gate that reinstalls and formats before it reaches the
    # thing that is broken costs most of what a repair loop costs. Empty where
    # the output does not say; then the caller runs the gate it would have run
    # anyway.
    @override
    def narrowed(self, ran: Ran) -> str:
        for part in (ran.stdout, ran.stderr):
            if found := _FAILED_TASK.search(_plain(part)):
                return f"mise run {found.group(1)}"
        return ""

    # A budget has no business here: this is the work list, and a tail of it
    # is an agent asked to cover lines it was never shown. Only where the
    # report never got printed does the trimmed log stand in for it.
    @override
    def coverage_report(self, ran: Ran) -> str:
        # Stripped before it is read, like every other reader here: a colour
        # code landing inside "Missing lines" would read a branch that left
        # lines uncovered as a branch that covered them, and push it.
        _, banner, rest = _plain(ran.stdout).partition(_BANNER)
        return banner + rest if banner else self.said(ran)

    # Read from the report because the exit code does not carry it: the task
    # runs `diff-cover` with no `--fail-under`, so a run naming missing lines
    # still ends 0. Both words and not just "Missing": the summary block says
    # "Missing: 0 lines" on a clean report too.
    @override
    def uncovered(self, report: str) -> bool:
        return _MISSING in report

    # Against everything the run has given up on, not just the last one: two
    # things broken at once alternate down the queue, and a memo of one
    # recognises neither.
    @override
    def already_seen(self, verdict: str, seen: list[str]) -> bool:
        return any(same_verdict(verdict, other) for other in seen)
