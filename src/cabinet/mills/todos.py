"""What one pull request needs next, read off the facts.

Facts make a todo; a label only takes one away. `pr::thermo` is a review
already posted and `v:guide:done` a guide already posted, and no label ever
adds work.
"""

import re

from typing_extensions import override

from cabinet.pacts.healing import TASKS, Facts, Surveyed, Task
from cabinet.pacts.project import Project
from cabinet.pacts.pulls import Board, Watched
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
    # The base has no pull request, so no number or threads: red on it is a
    # `ci` todo and nothing else.
    @override
    def base(self, board: Board, project: Project) -> Surveyed:
        red = _red(board, project)
        todos: list[Task] = ["ci"] if red else []
        return Surveyed(
            number=0, branch=project.base, url="", todos=todos, red=red, threads=0
        )

    @override
    def surveyed(self, facts: Facts, project: Project) -> Surveyed:
        pull = facts.pull
        red = _red(facts.board, project)
        # Threads that want an answer: a thread opened by someone else is
        # theirs to resolve, so it stops counting once the ritual has replied.
        threads = sum(thread.waits(project.bots) for thread in facts.threads)
        due: set[Task] = set()
        # Only a conflict: a branch behind its base merges fine.
        if facts.conflicted:
            due.add("merge")
        if red:
            due.add("ci")
        if not pull.wears(project.labels.reviewed):
            due.add("review")
        if threads:
            due.add("answer")
        # The endgame: asked for only once nothing else is left to do.
        if not due and not pull.wears(project.labels.qa):
            due.add("guide")
        found = [task for task in TASKS if task in due]
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
def _red(board: Board, project: Project) -> list[Watched]:
    red: dict[str, Watched] = {}
    for watched in board.watched(project):
        if watched.check.passed is False or _names_a_gap(watched):
            red.setdefault(watched.check.name, watched)
    return list(red.values())


def _names_a_gap(watched: Watched) -> bool:
    if not watched.job.covering or not watched.check.title:
        return False
    found = _DIFF_HIT.search(watched.check.title)
    return found is not None and float(found.group(1)) < WHOLE
