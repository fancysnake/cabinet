"""What the morning reads."""

from cabinet.mills.report import Report
from cabinet.pacts.issues import Identification, IdentifiedItem, Identifying, Issue
from cabinet.pacts.project import Project
from cabinet.pacts.pulls import Checked, PullRequest, Run
from cabinet.pacts.reviews import Picking, Reviewed
from cabinet.pacts.threads import Finding, TriageItem

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
            "refresh — 1 checked\n\n  #7 feature: green and reviewed, 0 unpushed\n"
        )

    @staticmethod
    def test_a_blocked_row_indents_its_note() -> None:
        row = _GREEN.model_copy(
            update={"outcome": "blocked", "unpushed": None, "note": "red:\n1 failed"}
        )

        assert _REPORT.sweep(_run(checked=[row])) == (
            "refresh — 1 checked\n\n"
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
        assert _REPORT.sweep(_run(mode="cover")) == "cover — 0 checked\n\n  (none)\n"

    @staticmethod
    def test_what_was_not_reached_and_why() -> None:
        assert _REPORT.sweep(_run(queue=[_PULL], stopped="gh died")) == (
            "refresh — 0 checked\n\n  (none)\n\n"
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
            "review — 2 branches\n  a: shipped\n"
            "  b: checked out elsewhere — worktree"
        )

    @staticmethod
    def test_nothing_reviewed() -> None:
        assert _REPORT.review(Picking(project=_PROJECT, bound=2)) == (
            "review — 0 branches\n  (none had a review waiting)"
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


class TestFindings:
    # The heading is for whoever opens the pull request and finds a comment on
    # their line. Nothing reads it back, so what it owes is a person.
    @staticmethod
    def test_every_item_is_headed_with_the_reviews_title() -> None:
        found = [
            Finding(path="src/thing.py", line=12, body="guard this"),
            Finding(path="", body="split the change"),
        ]

        assert _REPORT.findings(_PROJECT, found) == [
            Finding(
                path="src/thing.py",
                line=12,
                body="## Thermo-nuclear code quality review\n\nguard this",
            ),
            Finding(
                path="",
                body="## Thermo-nuclear code quality review\n\nsplit the change",
            ),
        ]

    @staticmethod
    def test_the_title_follows_the_config() -> None:
        project = _PROJECT.model_copy(update={"review_title": "Night review"})

        headed = _REPORT.findings(project, [Finding(path="", body="hm")])

        assert headed[0].body == "## Night review\n\nhm"


_ISSUE = Issue(number=5, title="t", url="https://example.test/5")


class TestIdentify:
    @staticmethod
    def test_every_ending_gets_its_line() -> None:
        identifying = Identifying(
            project=_PROJECT,
            identified=[
                Identification(
                    number=3,
                    outcome="identified",
                    item=IdentifiedItem(
                        number=3, kind="feature", size="M", blocked_by=[4]
                    ),
                ),
                Identification(
                    number=4,
                    outcome="identified",
                    item=IdentifiedItem(
                        number=4,
                        kind="edit",
                        epic=True,
                        children=[12],
                        note="split by layer",
                    ),
                    opened=[10, 11],
                ),
                Identification(
                    number=5,
                    outcome="identified",
                    item=IdentifiedItem(
                        number=5, kind="spike", note="need the metrics"
                    ),
                ),
                Identification(
                    number=6,
                    outcome="identified",
                    item=IdentifiedItem(
                        number=6, kind="bug", size="S", blocked_by=[3, 5]
                    ),
                    refused=["could not say #6 is blocked by #3: taken", "gh died"],
                ),
                Identification(number=7, outcome="missed"),
            ],
        )

        assert _REPORT.identify(identifying) == (
            "identify — 5 issues\n"
            "  #3 feature/M, linked #4\n"
            "  #4 edit/epic, opened #10 #11, linked #12 — split by layer\n"
            "  #5 spike/unsized — need the metrics\n"
            "  #6 bug/S, linked #3 #5\n"
            "    refused: could not say #6 is blocked by #3: taken\n"
            "    refused: gh died\n"
            "  #7: the agent did not answer for it"
        )

    # The page taken up and the rows saying what became of it are written
    # here, in one shape, so the two lists read as one.
    @staticmethod
    def test_the_page_is_offered_one_issue_a_line() -> None:
        assert _REPORT.page([_ISSUE, _ISSUE.model_copy(update={"number": 6})]) == (
            "  #5 t\n  #6 t"
        )

    @staticmethod
    def test_an_empty_page_is_an_empty_listing() -> None:
        assert not _REPORT.page([])

    # An issue past the end of the listing reads like an issue nothing wanted
    # doing to, so the count is said to be a count of what was seen.
    @staticmethod
    def test_a_backlog_the_forge_would_not_list_the_end_of_says_so() -> None:
        identifying = Identifying(project=_PROJECT, truncated=True)

        assert _REPORT.identify(identifying) == (
            "identify — 0 issues\n"
            "  (none wanted identifying)\n"
            "\n"
            "the forge listed as many of your open issues as it gives at once:"
            " there are more, and this cast never saw them"
        )

    @staticmethod
    def test_nothing_to_identify_says_so() -> None:
        assert _REPORT.identify(Identifying(project=_PROJECT)) == (
            "identify — 0 issues\n  (none wanted identifying)"
        )

    @staticmethod
    def test_a_stopped_cast_names_the_reason_and_what_was_never_reached() -> None:
        identifying = Identifying(
            project=_PROJECT,
            queue=[_ISSUE],
            identified=[Identification(number=2, outcome="stopped")],
            stopped="the agent stopped mid-flight",
        )

        assert _REPORT.identify(identifying) == (
            "identify — 1 issues\n"
            "  #2: on the page the cast stopped on; nothing was put on it\n"
            "\n"
            "the cast stopped: the agent stopped mid-flight\n"
            "not reached:    #5"
        )
