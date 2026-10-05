"""Which issues still want identifying, and which one a thread was filed as."""

import pytest

from cabinet.mills.backlog import Backlog
from cabinet.pacts.issues import Issue
from cabinet.pacts.threads import filed_for


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


class TestFiled:
    @staticmethod
    def test_the_issue_naming_the_thread_is_found() -> None:
        other = Issue(number=1, title="t", url="u1", body=filed_for("PRRT_2"))
        filed = Issue(number=2, title="t", url="u2", body=f"x\n\n{filed_for('PRRT_1')}")

        assert Backlog().filed([other, filed], "PRRT_1") == filed

    @staticmethod
    def test_no_issue_naming_the_thread_is_none() -> None:
        assert Backlog().filed([_issue()], "PRRT_1") is None
