"""What one pull request needs next, read off the facts.

Facts make a todo; a label only takes one away. `pr::thermo` is a review
already posted and `v:guide:done` a guide already posted, and no label ever
adds work.
"""

from typing_extensions import override

from cabinet.pacts.healing import Facts, Surveyed, Todo
from cabinet.pacts.project import Project
from cabinet.pacts.pulls import Board
from cabinet.pacts.services import TodosProtocol


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


# A check still running is not red: the next cast reads what it came to.
def _red(board: Board, project: Project) -> list[str]:
    named = (check.name for check in board.watched(project.ci) if check.passed is False)
    # A value spelled out: with none, or `None`, its values type as `Any`.
    return list(dict.fromkeys(named, True))
