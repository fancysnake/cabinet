"""Which issues still want identifying, and which one a thread was filed as."""

from typing_extensions import override

from cabinet.pacts.issues import EPIC, KINDS, SIZES, Issue
from cabinet.pacts.services import BacklogProtocol
from cabinet.pacts.threads import filed_for


class Backlog(BacklogProtocol):
    # Identified is a type and then a size, or a type and the epic label: an epic
    # is sized by its sub-issues, and asking for its own size again would bring
    # it back every cast.
    @override
    def unidentified(self, issues: list[Issue]) -> list[Issue]:
        return [one for one in issues if not _identified(one)]

    @override
    def filed(self, issues: list[Issue], thread: str) -> Issue | None:
        mark = filed_for(thread)
        return next((one for one in issues if mark in one.body), None)


def _identified(issue: Issue) -> bool:
    worn = set(issue.labels)
    typed = not worn.isdisjoint(KINDS)
    sized = not worn.isdisjoint(SIZES) or EPIC in worn
    return typed and sized
