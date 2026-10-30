"""Which issues still want identifying."""

import pytest

from cabinet.mills.backlog import Backlog
from cabinet.pacts.issues import Issue, Issues, Listing


def _issue(*labels: str, number: int = 1, mine: bool = False) -> Issue:
    return Issue(
        number=number,
        title="t",
        url=f"https://example.test/{number}",
        labels=list(labels),
        mine=mine,
    )


class TestMerged:
    @staticmethod
    def test_each_issue_once_lowest_number_first() -> None:
        issues = Issues(assigned=[_issue(number=9), _issue(number=2)])

        assert Backlog().merged(issues) == Listing(
            issues=[_issue(number=2), _issue(number=9)]
        )

    @staticmethod
    def test_an_issue_you_opened_is_yours_though_also_assigned() -> None:
        issues = Issues(authored=[_issue(number=4)], assigned=[_issue(number=4)])

        assert Backlog().merged(issues).issues == [_issue(number=4, mine=True)]

    @staticmethod
    def test_an_issue_you_are_only_assigned_is_not_yours() -> None:
        issues = Issues(authored=[_issue(number=3)], assigned=[_issue(number=8)])

        assert Backlog().merged(issues).issues == [
            _issue(number=3, mine=True),
            _issue(number=8),
        ]

    @staticmethod
    @pytest.mark.parametrize("truncated", [True, False])
    def test_whether_the_forge_cut_it_short_passes_through(*, truncated: bool) -> None:
        issues = Issues(assigned=[_issue()], truncated=truncated)

        assert Backlog().merged(issues).truncated is truncated


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
