"""What the report says, on the terminal and on the pull request."""

from textwrap import fill

from typing_extensions import override

from cabinet.pacts.healing import Checked, Run, Surveyed, Task, Unsurveyed
from cabinet.pacts.issues import (
    EPIC,
    Identification,
    IdentifiedItem,
    Identifying,
    Issue,
    Left,
)
from cabinet.pacts.project import Project
from cabinet.pacts.pulls import PullRequest
from cabinet.pacts.services import ReportProtocol
from cabinet.pacts.threads import ITEM, Finding, Thread, TriageItem
from cabinet.specs import CARD_WIDTH

_OUTCOME = {"worked": "worked", "blocked": "blocked", "skipped": "left alone"}

_WAITING = "waiting for you, cast without --unattended:"


_LEFT = {
    "missed": "the agent did not answer for it",
    "stopped": "on the page the cast stopped on; nothing was put on it",
}


def _numbers(numbers: list[int]) -> str:
    return " ".join(f"#{number}" for number in numbers)


# An epic carries no size because its parts carry it; an issue the agent
# would not size carries none either. Different answers, so the line says
# which rather than reading one as the other.
def _sized(item: IdentifiedItem) -> str:
    if item.epic:
        return EPIC
    return item.size or "unsized"


# What went on one issue, on one line: `#12 feature/M`, or an epic with the
# sub-issues opened under it, then what it was linked to and the note, then
# each write the forge refused on it, a line apiece.
def _identified(row: Identification) -> str:
    if isinstance(row, Left):
        return f"  #{row.number}: {_LEFT[row.outcome]}"
    item = row.item
    opened = f", opened {_numbers(row.opened)}" if row.opened else ""
    line = f"  #{row.number} {item.kind}/{_sized(item)}{opened}"
    if linked := [*item.children, *item.blocked_by]:
        line += f", linked {_numbers(linked)}"
    line += f" — {item.note}" if item.note else ""
    return "\n".join([line, *(f"    refused: {one}" for one in row.refused)])


# p1 sorts before p4, and sorted is stable, so the reading's order holds within
# a priority. A typed key: strict mypy refuses a lambda here.
def _priority(item: TriageItem) -> str:
    return item.priority


_TAKES = (
    "Press return to take the action above, or answer fix, reject or file,\n"
    "or say in your own words what should happen.\n->"
)

# Estimate is the longest of the six labels, which spell TRIAGE.
_LABEL = len("Estimate: ")


# A label and its value, wrapped lines indented under the value so the label
# column holds labels only. Each line of the value wraps on its own, so proof
# that is code or command output keeps its lines. A path longer than the line
# stays whole: one broken across lines cannot be copied. A command with spaces
# in it can still break at them. A blank line keeps its label, which `fill`
# alone would drop.
def _row(label: str, value: str) -> str:
    pad = " " * _LABEL
    rows = []
    for index, line in enumerate(value.splitlines() or [""]):
        head = f"{label}:".ljust(_LABEL) if index == 0 else pad
        rows.append(
            fill(
                line,
                CARD_WIDTH,
                initial_indent=head,
                subsequent_indent=pad,
                break_long_words=False,
                break_on_hyphens=False,
            )
            or head.rstrip()
        )
    return "\n".join(rows)


def _title(text: str) -> str:
    return f"── {text} ".ljust(CARD_WIDTH, "─")


# One thread, for somebody who has forgotten the code and decides from this
# alone. Plain text, so it reads the same on a terminal, in the TUI and in a
# chat channel. The six labels spell TRIAGE. Two halves: what the thread said,
# then what the reading would do, its title naming the action a return key
# takes. The Action row repeats the verb: `what` holds the reason, and the
# card also goes to the answer agent, which reads the row, not the title.
def _card(head: str, item: TriageItem, author: str) -> str:
    by = f", raised by {author}" if author else ""
    files = "1 file" if item.files == 1 else f"{item.files} files"
    return "\n".join(
        [
            head,
            "",
            _title("The thread"),
            _row("Thread", f"{item.where}{by}"),
            _row("Raised", item.raised),
            _row("If left", item.left),
            "",
            _title(f"The reading would {item.action.upper()} it"),
            _row("Action", f"{item.action} — {item.what}"),
            _row("Grounds", f"{item.grounds} — {item.proof}"),
            _row("Estimate", f"{item.size}, {files}, {item.risk} risk"),
        ]
    )


# A todo with what it would work through, where that is more than its name.
def _todo(row: Surveyed, todo: Task) -> str:
    if todo == "ci":
        return f"ci ({', '.join(red.check.name for red in row.red)})"
    if todo == "answer":
        return f"answer ({_threads(row.threads)})"
    return todo


def _threads(count: int) -> str:
    return f"{count} thread" if count == 1 else f"{count} threads"


# A branch `heal.main` works has no pull request, so no number, until it opens
# one.
def _head(number: int, branch: str) -> str:
    return f"#{number} {branch}" if number else branch


def _line(row: Checked) -> str:
    ahead = "unknown" if row.unpushed is None else f"{row.unpushed} unpushed"
    # A blocked row's note carries the gate's verdict, which is a dozen lines
    # of someone else's output. Indented under the row rather than run into
    # it: the rows are a scannable list, and a note that starts in column zero
    # ends that list wherever it lands.
    wrapped = row.note.replace("\n", "\n      ")
    note = f" — {wrapped}" if row.note else ""
    head = _head(row.number, row.branch)
    return f"  {head}: {_OUTCOME[row.outcome]}, {ahead}{note}"


# Said wherever the forge stopped listing `what` at its cap: one the listing
# never reached looks exactly like one nothing wanted doing to.
def _cut_short(what: str) -> str:
    return (
        f"the forge listed as many of your open {what} as it gives at once:"
        " there may be more, and this cast would not have seen them"
    )


# What follows a heal cast's rows, however it took its branches.
def _ending(run: Run, lines: list[str]) -> str:
    # Said wherever the cast left any, as the way to get them answered: a
    # cast nobody attended answers nothing, and says so here rather than
    # leaving the survey line to look like work it did not do.
    if waiting := run.waiting():
        lines += ["", _WAITING]
        lines += [
            f"  #{row.number} {row.branch}: {_threads(row.threads)}" for row in waiting
        ]
    if run.truncated:
        lines += ["", _cut_short("pull requests")]
    # Only when there are any, unlike the rows: a cast that reached every
    # pull request is the normal one, and a line saying "none" on every
    # one of them trains the eye past it. A cast that failed left them
    # behind; one out of steps took none it could not finish, and a smaller
    # bound or fewer CI jobs is what fits them.
    not_reached = ", ".join(pull.branch for pull in run.queue)
    if run.failed():
        why = run.stopped or f"branches blocked: {len(run.blocked())}"
        lines += ["", f"not reached: {not_reached}"] if not_reached else []
        lines += ["", f"the cast failed: {why}"]
    elif not_reached:
        lines += [
            "",
            f"out of steps at this --bound and CI jobs, not reached: {not_reached}",
        ]
    return "\n".join(lines) + "\n"


class Report(ReportProtocol):
    # The heading is for whoever opens the pull request and finds a comment on
    # their line: it says which review said it, so the ritual's items can be
    # told from a colleague's by eye. The hidden mark after it is what `answer`
    # knows a plain comment for one of the review's items by, where the forge
    # would not anchor the item to its line.
    @override
    def findings(self, project: Project, found: list[Finding]) -> list[Finding]:
        return [
            Finding(
                path=one.path,
                line=one.line,
                body=f"## {project.review_title}\n\n{one.body}\n\n{ITEM}",
            )
            for one in found
        ]

    @override
    def healed(self, run: Run) -> str:
        lines = [f"heal — {len(run.checked)} worked", ""]
        lines += [_line(row) for row in run.checked] or ["  (none)"]
        return _ending(run, lines)

    # The page as it goes to the agent, before anything is read or written: the
    # same indent and the same `#n` as the rows that say what became of it, so
    # what was taken up and what came back of it read as one list.
    @override
    def page(self, issues: list[Issue]) -> str:
        return "\n".join(f"  #{one.number} {one.title}" for one in issues)

    @override
    def identify(self, identifying: Identifying) -> str:
        lines = [f"identify — {len(identifying.identified)} issues"]
        lines += [_identified(row) for row in identifying.identified] or [
            "  (none wanted identifying)"
        ]
        # The count above is a count of what was seen.
        if identifying.truncated:
            lines += ["", _cut_short("issues")]
        if identifying.stopped:
            lines += ["", f"the cast stopped: {identifying.stopped}"]
            if left := identifying.queue:
                lines += [f"not reached:    {_numbers([one.number for one in left])}"]
        return "\n".join(lines)

    # `#7 feature: merge, ci (checks), answer (3 threads), review`.
    @override
    def surveyed(self, row: Surveyed | Unsurveyed) -> str:
        head = _head(row.number, row.branch)
        # Indented the way a worked row's note is: git's complaint is often
        # stdout and stderr on lines of their own, and one in column zero
        # reads as the next pull request.
        if isinstance(row, Unsurveyed):
            wrapped = row.note.replace("\n", "\n    ")
            return f"{head}: could not survey: {wrapped}"
        todos = [_todo(row, todo) for todo in row.todos]
        return f"{head}: {', '.join(todos) or 'nothing to do'}"

    # The priority orders the cards and shows on none: what must be fixed
    # before the merge is asked first.
    @override
    def cards(
        self, pull: PullRequest, items: list[TriageItem], threads: list[Thread]
    ) -> list[tuple[TriageItem, str]]:
        raised = {thread.id: thread.raised_by for thread in threads}
        ordered = sorted(items, key=_priority)
        return [
            (
                item,
                _card(
                    f"#{pull.number} {pull.title} — thread {index} of {len(ordered)}",
                    item,
                    raised[item.thread],
                ),
            )
            for index, item in enumerate(ordered, start=1)
        ]

    @override
    def asked(self, card: str) -> str:
        return f"{card}\n\n{_TAKES}"
