"""Which issues still want refining."""

from typing_extensions import override

from cabinet.pacts.issues import Issue
from cabinet.pacts.project import EPIC, KINDS, SIZES
from cabinet.pacts.services import BacklogProtocol


class Backlog(BacklogProtocol):
    # Refined is a type and then a size, or a type and the epic label: an epic
    # is sized by its sub-issues, and asking for its own size again would bring
    # it back every cast.
    @override
    def unrefined(self, issues: list[Issue]) -> list[Issue]:
        return [one for one in issues if not _refined(one)]


def _refined(issue: Issue) -> bool:
    worn = set(issue.labels)
    typed = not worn.isdisjoint(KINDS)
    sized = not worn.isdisjoint(SIZES) or EPIC in worn
    return typed and sized
