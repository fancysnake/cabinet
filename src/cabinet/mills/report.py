"""What the morning reads, on the terminal and on the pull request."""

from collections import Counter
from itertools import starmap

from typing_extensions import override

from cabinet.pacts.issues import (
    EPIC,
    Identification,
    IdentifiedItem,
    Identifying,
    Issue,
)
from cabinet.pacts.project import Project
from cabinet.pacts.pulls import Checked, Run
from cabinet.pacts.reviews import Picking
from cabinet.pacts.services import ReportProtocol
from cabinet.pacts.threads import Finding, TriageItem

_OUTCOME = {
    "green": "green and reviewed",
    "blocked": "blocked",
    "skipped": "left alone",
}

_TOLD = {
    "shipped": "shipped",
    "declined": "left for later",
    "elsewhere": "checked out elsewhere",
    "unread": "the forge would not say what is open",
    "nothing": "the reading found nothing",
    "stopped": "stopped the cast",
}

_PRIORITIES = ("p1", "p2", "p3", "p4")

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
    if (item := row.item) is None:
        return f"  #{row.number}: {_LEFT[row.outcome]}"
    opened = f", opened {_numbers(row.opened)}" if row.opened else ""
    line = f"  #{row.number} {item.kind}/{_sized(item)}{opened}"
    if linked := [*item.children, *item.blocked_by]:
        line += f", linked {_numbers(linked)}"
    line += f" — {item.note}" if item.note else ""
    return "\n".join([line, *(f"    refused: {one}" for one in row.refused)])


# What the thread asked and what the reading would do about it, in that
# order: this is read on a terminal by somebody deciding what to do with it,
# and the verdict alone does not say what it is a verdict on. Written here and
# nowhere else because the agent that acts on the triage is handed these same
# lines with your answer under each — what you decided about and what it is
# told you decided about have to be the same text.
def triage_line(index: int, item: TriageItem) -> str:
    return (
        f"{index}. [{item.priority}/{item.action}] {item.where} — {item.raised}\n"
        f"   -> {item.what}"
    )


def _line(row: Checked) -> str:
    ahead = "unknown" if row.unpushed is None else f"{row.unpushed} unpushed"
    # A blocked row's note carries the gate's verdict, which is a dozen lines
    # of someone else's output. Indented under the row rather than run into
    # it: the rows are a scannable list, and a note that starts in column zero
    # ends that list wherever it lands.
    wrapped = row.note.replace("\n", "\n      ")
    note = f" — {wrapped}" if row.note else ""
    return f"  #{row.number} {row.branch}: {_OUTCOME[row.outcome]}, {ahead}{note}"


class Report(ReportProtocol):
    # The heading is for whoever opens the pull request and finds a comment on
    # their line: it says which review said it, so the night's items can be
    # told from a colleague's by eye. Nothing reads it back — `review` triages
    # every unresolved thread whoever wrote it — so it is a courtesy to a
    # reader and not a marker anything matches on.
    @override
    def findings(self, project: Project, found: list[Finding]) -> list[Finding]:
        return [
            Finding(
                path=one.path,
                line=one.line,
                body=f"## {project.review_title}\n\n{one.body}",
            )
            for one in found
        ]

    @override
    def sweep(self, run: Run) -> str:
        lines = [f"{run.mode} — {len(run.checked)} checked", ""]
        lines += [_line(row) for row in run.checked] or ["  (none)"]
        # Only when there are any, unlike the rows: a pass that reached every
        # pull request is the normal night, and a line saying "none" on every
        # one of them trains the eye past it.
        if not_reached := [pull.branch for pull in run.queue]:
            lines += ["", f"not reached: {', '.join(not_reached)}"]
        if run.stopped:
            lines += ["", f"the run failed: {run.stopped}"]
        return "\n".join(lines) + "\n"

    @override
    def review(self, picking: Picking) -> str:
        lines = [f"review — {len(picking.reviewed)} branches"]
        lines += [
            f"  {row.branch}: {_TOLD[row.outcome]}"
            + (f" — {row.note}" if row.note else "")
            for row in picking.reviewed
        ] or ["  (none had a review waiting)"]
        # A cast that ran to the end left nothing in the queue. One that
        # stopped left branches the forge was never asked about, not branches
        # with work outstanding; one out of steps left branches that may have.
        left = ", ".join(pull.branch for pull in picking.queue)
        if picking.stopped:
            lines += ["", f"the cast stopped: {picking.stopped}"]
            lines += [f"not polled:     {left}"] if left else []
        elif left:
            lines += ["", f"out of steps, left for the next cast: {left}"]
        return "\n".join(lines)

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
        # An issue the listing never reached looks exactly like one nothing
        # wanted doing to, so the count above is a count of what was seen.
        if identifying.truncated:
            lines += [
                "",
                (
                    "the forge listed as many of your open issues as it gives at"
                    " once: there are more, and this cast never saw them"
                ),
            ]
        if identifying.stopped:
            lines += ["", f"the cast stopped: {identifying.stopped}"]
            if left := identifying.queue:
                lines += [f"not reached:    {_numbers([one.number for one in left])}"]
        return "\n".join(lines)

    # The whole triage, headed by a tally, for the terminal.
    @override
    def triage(self, items: list[TriageItem]) -> list[str]:
        tally: Counter[str] = Counter(item.priority for item in items)
        counted = ", ".join(f"{p}: {tally[p]}" for p in _PRIORITIES)
        shown = starmap(self.shown, enumerate(items, start=1))
        return [f"{len(items)} outstanding — {counted}", "", *shown]

    @override
    def shown(self, index: int, item: TriageItem) -> str:
        return triage_line(index, item)
