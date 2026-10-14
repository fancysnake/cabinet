"""What one pull request needs next, read off the facts.

Facts make a todo; a label only takes one away. `pr::thermo` is a review
already posted and `v:guide:done` a guide already posted, and no label ever
adds work.
"""

from typing_extensions import override

from cabinet.pacts.healing import Facts, Todo
from cabinet.pacts.project import Project
from cabinet.pacts.pulls import Board
from cabinet.pacts.services import TodosProtocol


class Todos(TodosProtocol):
    @override
    def todos(self, facts: Facts, project: Project) -> list[Todo]:
        pull = facts.pull
        found: list[Todo] = []
        # Only a conflict: a branch behind its base merges fine.
        if facts.conflicted:
            found.append("merge")
        if self.red(facts.board, project):
            found.append("ci")
        # Whoever opened them: agents post with the owner's token, so the
        # author says nothing about whether a thread wants an answer.
        if any(not thread.resolved for thread in facts.threads):
            found.append("answer")
        if not pull.wears(project.labels.reviewed):
            found.append("review")
        # The endgame: asked for only once nothing else is left to do.
        if not found and not pull.wears(project.labels.qa):
            found.append("guide")
        return found

    # A check still running is not red: the next cast reads what it came to.
    @override
    def red(self, board: Board, project: Project) -> list[str]:
        named = (
            check.name
            for check in board.checks
            if check.passed is False and project.ci.job(check.name) is not None
        )
        return list(dict.fromkeys(named, True))
