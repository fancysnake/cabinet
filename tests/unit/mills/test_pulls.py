"""Which pull requests are taken."""

from cabinet.mills.pulls import Pulls
from cabinet.pacts.project import Project
from cabinet.pacts.pulls import PullRequest

_PULLS = Pulls()
_PROJECT = Project()


def _pull(
    number: int, *, updated_at: str, labels: list[str] | None = None
) -> PullRequest:
    return PullRequest(
        number=number,
        title=f"pr {number}",
        url=f"https://example.test/pull/{number}",
        branch=f"feature-{number}",
        base="main",
        updated_at=updated_at,
        labels=labels or [],
    )


class TestWanted:
    @staticmethod
    def test_oldest_modified_first() -> None:
        newer = _pull(1, updated_at="2026-08-02T00:00:00Z")
        older = _pull(2, updated_at="2026-08-01T00:00:00Z")

        assert _PULLS.wanted([newer, older], _PROJECT) == [older, newer]

    @staticmethod
    def test_a_parked_branch_is_dropped() -> None:
        parked = _pull(1, updated_at="2026-08-01T00:00:00Z", labels=["pr::wait"])
        wanted = _pull(2, updated_at="2026-08-02T00:00:00Z")

        assert _PULLS.wanted([parked, wanted], _PROJECT) == [wanted]

    @staticmethod
    def test_the_wait_label_is_the_projects() -> None:
        project = Project.model_validate({"labels": {"wait": "hold"}})
        parked = _pull(1, updated_at="2026-08-01T00:00:00Z", labels=["hold"])
        not_parked = _pull(2, updated_at="2026-08-02T00:00:00Z", labels=["pr::wait"])

        assert _PULLS.wanted([parked, not_parked], project) == [not_parked]


class TestAt:
    @staticmethod
    def test_only_the_branch_asked_for() -> None:
        here = _pull(1, updated_at="2026-08-01T00:00:00Z")
        elsewhere = _pull(2, updated_at="2026-08-01T00:00:00Z")

        assert _PULLS.at([elsewhere, here], "feature-1") == [here]

    @staticmethod
    def test_one_head_against_two_bases_is_both() -> None:
        into_main = _pull(1, updated_at="2026-08-01T00:00:00Z")
        into_release = into_main.model_copy(update={"number": 2, "base": "release"})

        assert _PULLS.at([into_main, into_release], "feature-1") == [
            into_main,
            into_release,
        ]
