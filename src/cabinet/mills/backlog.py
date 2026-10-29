"""Your open issues once each, and which still want identifying."""

from typing_extensions import override

from cabinet.pacts.issues import EPIC, KINDS, SIZES, Issue, Listing
from cabinet.pacts.services import BacklogProtocol


class Backlog(BacklogProtocol):
    # An issue you opened and are assigned is listed twice, and it is yours
    # whichever listing came first.
    @override
    def listed(self, listing: Listing) -> Listing:
        found: dict[int, Issue] = {}
        for one in listing.issues:
            if one.number not in found or one.mine:
                found[one.number] = one
        return Listing(
            issues=[found[number] for number in sorted(found)],
            truncated=listing.truncated,
        )

    # Identified is a type and then a size, or a type and the epic label: an epic
    # is sized by its sub-issues, and asking for its own size again would bring
    # it back every cast.
    @override
    def unidentified(self, issues: list[Issue]) -> list[Issue]:
        return [one for one in issues if not _identified(one)]


def _identified(issue: Issue) -> bool:
    worn = set(issue.labels)
    typed = not worn.isdisjoint(KINDS)
    sized = not worn.isdisjoint(SIZES) or EPIC in worn
    return typed and sized
