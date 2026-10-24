"""What one pull request needs next, read off the facts.

Facts make a todo; a label only takes one away. `pr::thermo` is a review
already posted and `v:guide:done` a guide already posted, and no label ever
adds work.
"""

import re

from typing_extensions import override

from cabinet.pacts.healing import Facts, Surveyed, Todo
from cabinet.pacts.project import Project
from cabinet.pacts.pulls import Board, Check
from cabinet.pacts.services import TodosProtocol
from cabinet.specs import WHOLE

# The patch check's own summary, which its check carries whether the check
# went green or not: "96.84% of diff hit (target 96.00%)". That green is the
# reason to read the number at all — a patch target below 100 passes a branch
# carrying lines no test touched, and this field is the only place that gap
# is named. A patch with nothing to measure says "Coverage not affected"
# instead and matches nothing here, which is the right reading.
_DIFF_HIT = re.compile(r"([\d.]+)% of diff hit")


class Todos(TodosProtocol):
    @override
    def surveyed(self, facts: Facts, project: Project) -> Surveyed:
        pull = facts.pull
        red = _red(facts.board, project)
        # Whoever opened them: agents post with the owner's token, so the
        # author says nothing about whether a thread wants an answer.
        threads = sum(not thread.resolved for thread in facts.threads)
        found: list[Todo] = []
        # Only a conflict: a branch behind its base merges fine.
        if facts.conflicted:
            found.append("merge")
        if red:
            found.append("ci")
        if threads:
            found.append("answer")
        if not pull.wears(project.labels.reviewed):
            found.append("review")
        # The endgame: asked for only once nothing else is left to do.
        if not found and not pull.wears(project.labels.qa):
            found.append("guide")
        return Surveyed(
            number=pull.number,
            branch=pull.branch,
            url=pull.url,
            todos=found,
            red=red,
            threads=threads,
        )


# A check still running is not red: the next cast reads what it came to. A
# green patch check naming a gap is, because the coverage is not right yet.
# One per name, the first the board lists.
def _red(board: Board, project: Project) -> list[Check]:
    red: dict[str, Check] = {}
    for check in board.watched(project.ci):
        if check.passed is False or _names_a_gap(check, project):
            red.setdefault(check.name, check)
    return list(red.values())


def _names_a_gap(check: Check, project: Project) -> bool:
    if not project.ci.covering(check.name) or not check.title:
        return False
    found = _DIFF_HIT.search(check.title)
    return found is not None and float(found.group(1)) < WHOLE
