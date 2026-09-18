"""Which pull requests the night takes, and what the check board says."""

import re
from typing import TYPE_CHECKING, override

from cabinet.pacts.services import PullsProtocol
from cabinet.specs import WHOLE

if TYPE_CHECKING:
    from cabinet.pacts.project import Project
    from cabinet.pacts.pulls import Board, Check, PullRequest

# The patch check's own summary, which its check carries whether the check
# went green or not: "96.84% of diff hit (target 96.00%)". That green is the
# reason to read the number at all — a patch target below 100 passes a branch
# carrying lines no test touched, and this field is the only place that gap
# is named. A patch with nothing to measure says "Coverage not affected"
# instead and matches nothing here, which is the right reading.
_DIFF_HIT = re.compile(r"([\d.]+)% of diff hit")


# A sort key, spelled out: `attrgetter` is `attrgetter[Any]` and a lambda's
# parameter is untyped, so a strict checker rejects both.
def _modified(pull: PullRequest) -> str:
    return pull.updated_at


class Pulls(PullsProtocol):
    # Parked branches are dropped here rather than skipped later, so one is
    # never checked out, never counted as reached, and never in a report at
    # all. Oldest-modified first: the branch drifting from its base the longest
    # is the one most likely to need the night.
    @override
    def wanted(self, pulls: list[PullRequest], project: Project) -> list[PullRequest]:
        wait = project.labels.wait
        return sorted((pull for pull in pulls if not pull.wears(wait)), key=_modified)

    # True unless the board positively says otherwise: a short board, a branch
    # CI has not reported on yet — all of them mean nobody has said the
    # coverage is fine, and the slow pass is the thing that finds out.
    @override
    def wants_cover(self, board: Board, project: Project) -> bool:
        patch = project.ci.patch_check
        if board.truncated or any(_names_a_gap(check, patch) for check in board.checks):
            return True
        watched = _watched(board, project.ci.cover_checks)
        return not watched or any(check.passed is not True for check in watched)

    # False where nobody has said — an empty board, a check still running —
    # because the gate is what finds out, and a skip granted on silence is a
    # red branch pushed and reviewed as green.
    @override
    def gates_green(self, board: Board, project: Project) -> bool:
        if board.truncated:
            return False
        watched = _watched(board, project.ci.gate_checks)
        return bool(watched) and all(check.passed is True for check in watched)


def _watched(board: Board, prefixes: list[str]) -> list[Check]:
    return [check for check in board.checks if check.name.startswith(tuple(prefixes))]


def _names_a_gap(check: Check, patch: str) -> bool:
    if check.name != patch or not check.title:
        return False
    found = _DIFF_HIT.search(check.title)
    return found is not None and float(found.group(1)) < WHOLE
