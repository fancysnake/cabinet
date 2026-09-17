"""What the morning reads."""

from collections import Counter
from itertools import starmap
from typing import TYPE_CHECKING, override

from cabinet.pacts.services import ReportProtocol

if TYPE_CHECKING:
    from cabinet.pacts.pulls import Checked, Run
    from cabinet.pacts.reviews import Picking
    from cabinet.pacts.threads import TriageItem

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
}

_PRIORITIES = ("p1", "p2", "p3", "p4")


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
    @override
    def sweep(self, run: Run) -> str:
        lines = [f"pr_{run.mode} — {len(run.checked)} checked", ""]
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
        lines = [f"pr_review — {len(picking.reviewed)} branches"]
        lines += [
            f"  {row.branch}: {_TOLD[row.outcome]}"
            + (f" — {row.note}" if row.note else "")
            for row in picking.reviewed
        ] or ["  (none had a review waiting)"]
        if picking.stopped:
            # What is left in the queue only means anything here: a cast that
            # ran to the end left nothing in it. These are branches the forge
            # was never asked about, not branches with work outstanding.
            left = ", ".join(pull.branch for pull in picking.queue)
            lines += ["", f"the cast stopped: {picking.stopped}"]
            lines += [f"not polled:     {left}"] if left else []
        return "\n".join(lines)

    # The whole triage, headed by a tally, for the terminal.
    @override
    def triage(self, items: list[TriageItem]) -> list[str]:
        tally: Counter[str] = Counter(item.priority for item in items)
        counted = ", ".join(f"{p}: {tally[p]}" for p in _PRIORITIES)
        shown = starmap(self.shown, enumerate(items, start=1))
        return [f"{len(items)} outstanding — {counted}", "", *shown]

    # What the thread asked and what the reading would do about it, in that
    # order: this is read on a terminal by somebody deciding what to do with
    # it, and the verdict alone does not say what it is a verdict on.
    @override
    def shown(self, index: int, item: TriageItem) -> str:
        return (
            f"{index}. [{item.priority}/{item.action}] {item.where} — {item.raised}\n"
            f"   -> {item.what}"
        )
