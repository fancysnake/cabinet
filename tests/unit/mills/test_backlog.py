"""Which issues still want identifying."""

import pytest

from cabinet.mills.backlog import Backlog
from cabinet.pacts.issues import Issue


def _issue(*labels: str) -> Issue:
    return Issue(number=1, title="t", url="https://example.test/1", labels=list(labels))


class TestUnidentified:
    @staticmethod
    @pytest.mark.parametrize(
        "labels", [(), ("feature",), ("M",), ("epic",), ("backlog", "P1")]
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
