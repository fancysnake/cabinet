"""Which pull requests a cast takes."""

from typing_extensions import override

from cabinet.pacts.project import Project
from cabinet.pacts.pulls import PullRequest
from cabinet.pacts.services import PullsProtocol


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

    # Every one, not the first: the same head opened against two bases is two
    # pull requests, and both are yours to hear about.
    @override
    def at(self, pulls: list[PullRequest], branch: str) -> list[PullRequest]:
        return [pull for pull in pulls if pull.branch == branch]
