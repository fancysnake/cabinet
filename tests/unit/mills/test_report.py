"""What the morning reads."""

from cabinet.mills.report import Report
from cabinet.pacts.project import Project
from cabinet.pacts.pulls import Checked, PullRequest, Run
from cabinet.pacts.reviews import Picking, Reviewed
from cabinet.pacts.threads import TriageItem

_REPORT = Report()
_PROJECT = Project()

_PULL = PullRequest(
    number=7,
    title="Add the thing",
    url="https://example.test/pull/7",
    branch="feature",
    base="main",
    updated_at="2026-08-01T22:00:00Z",
)

_GREEN = Checked(number=7, branch="feature", url=_PULL.url, outcome="green", unpushed=0)


def _run(**update: object) -> Run:
    return Run(project=_PROJECT, bound=3).model_copy(update=update)


class TestSweep:
    @staticmethod
    def test_a_green_row() -> None:
        assert _REPORT.sweep(_run(checked=[_GREEN])) == (
            "pr_refresh — 1 checked\n\n  #7 feature: green and reviewed, 0 unpushed\n"
        )

    @staticmethod
    def test_a_blocked_row_indents_its_note() -> None:
        row = _GREEN.model_copy(
            update={"outcome": "blocked", "unpushed": None, "note": "red:\n1 failed"}
        )

        assert _REPORT.sweep(_run(checked=[row])) == (
            "pr_refresh — 1 checked\n\n"
            "  #7 feature: blocked, unknown — red:\n      1 failed\n"
        )

    @staticmethod
    def test_a_skipped_row() -> None:
        row = _GREEN.model_copy(update={"outcome": "skipped", "unpushed": None})

        assert "  #7 feature: left alone, unknown\n" in _REPORT.sweep(
            _run(checked=[row])
        )

    @staticmethod
    def test_nothing_checked() -> None:
        assert _REPORT.sweep(_run(mode="cover")) == "pr_cover — 0 checked\n\n  (none)\n"

    @staticmethod
    def test_what_was_not_reached_and_why() -> None:
        assert _REPORT.sweep(_run(queue=[_PULL], stopped="gh died")) == (
            "pr_refresh — 0 checked\n\n  (none)\n\n"
            "not reached: feature\n\nthe run failed: gh died\n"
        )


class TestReview:
    @staticmethod
    def test_rows_and_their_notes() -> None:
        picking = Picking(
            project=_PROJECT,
            bound=2,
            reviewed=[
                Reviewed(branch="a", outcome="shipped"),
                Reviewed(branch="b", outcome="elsewhere", note="worktree"),
            ],
        )

        assert _REPORT.review(picking) == (
            "pr_review — 2 branches\n  a: shipped\n"
            "  b: checked out elsewhere — worktree"
        )

    @staticmethod
    def test_nothing_reviewed() -> None:
        assert _REPORT.review(Picking(project=_PROJECT, bound=2)) == (
            "pr_review — 0 branches\n  (none had a review waiting)"
        )

    @staticmethod
    def test_a_stopped_cast_names_what_it_never_polled() -> None:
        picking = Picking(project=_PROJECT, bound=2, queue=[_PULL], stopped="red")

        assert _REPORT.review(picking).endswith(
            "\n\nthe cast stopped: red\nnot polled:     feature"
        )


class TestTriage:
    @staticmethod
    def test_the_tally_and_every_item() -> None:
        item = TriageItem(
            where="src/thing.py",
            raised="add a guard",
            what="the guard is missing",
            priority="p1",
            action="fix",
            thread="T1",
        )

        assert _REPORT.triage([item, item.model_copy(update={"priority": "p4"})]) == [
            "2 outstanding — p1: 1, p2: 0, p3: 0, p4: 1",
            "",
            "1. [p1/fix] src/thing.py — add a guard\n   -> the guard is missing",
            "2. [p4/fix] src/thing.py — add a guard\n   -> the guard is missing",
        ]
