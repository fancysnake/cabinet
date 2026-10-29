"""Which issues still want identifying."""

import pytest

from cabinet.mills.backlog import Backlog
from cabinet.pacts.issues import Issue, Listing


def _issue(*labels: str) -> Issue:
    return Issue(number=1, title="t", url="https://example.test/1", labels=list(labels))


def _numbered(number: int, *, mine: bool = False) -> Issue:
    return Issue(
        number=number, title="t", url=f"https://example.test/{number}", mine=mine
    )


class TestListed:
    @staticmethod
    def test_each_issue_once_lowest_number_first() -> None:
        listing = Listing(issues=[_numbered(9), _numbered(2), _numbered(9)])

        assert Backlog().listed(listing) == Listing(issues=[_numbered(2), _numbered(9)])

    @staticmethod
    @pytest.mark.parametrize("mine_first", [True, False])
    def test_an_issue_you_opened_stays_yours_though_also_assigned(
        *, mine_first: bool
    ) -> None:
        both = [_numbered(4, mine=True), _numbered(4)]
        listing = Listing(issues=both if mine_first else both[::-1])

        assert Backlog().listed(listing).issues == [_numbered(4, mine=True)]

    @staticmethod
    @pytest.mark.parametrize("truncated", [True, False])
    def test_whether_the_forge_cut_it_short_passes_through(*, truncated: bool) -> None:
        listing = Listing(issues=[_numbered(1)], truncated=truncated)

        assert Backlog().listed(listing).truncated is truncated


class TestUnidentified:
    @staticmethod
    @pytest.mark.parametrize(
        "labels",
        [(), ("feature",), ("M",), ("epic",), ("spike", "M"), ("backlog", "P1")],
    )
    def test_missing_a_type_or_a_size_is_unidentified(labels: tuple[str, ...]) -> None:
        issue = _issue(*labels)

        assert Backlog().unidentified([issue]) == [issue]

    @staticmethod
    @pytest.mark.parametrize(
        "labels", [("feature", "M"), ("bug", "S", "backlog"), ("chore", "epic")]
    )
    def test_a_type_and_a_size_or_the_epic_label_is_identified(
        labels: tuple[str, ...],
    ) -> None:
        assert Backlog().unidentified([_issue(*labels)]) == []
