"""What the report says, on the terminal and on the pull request."""

from cabinet.mills.report import Report
from cabinet.pacts.healing import Checked, Run, Surveyed, Unsurveyed
from cabinet.pacts.issues import Identification, IdentifiedItem, Identifying, Issue
from cabinet.pacts.project import Project
from cabinet.pacts.pulls import Check, PullRequest
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

_WORKED = Checked(
    number=7, branch="feature", url=_PULL.url, outcome="worked", unpushed=0
)

_ANSWER = Surveyed(
    number=7, branch="feature", url=_PULL.url, todos=["answer"], red=[], threads=11
)


def _run(**update: object) -> Run:
    return Run(project=_PROJECT).model_copy(update=update)


class TestHealed:
    @staticmethod
    def test_a_green_row() -> None:
        assert _REPORT.healed(_run(checked=[_WORKED])) == (
            "heal — 1 worked\n\n  #7 feature: worked, 0 unpushed\n"
        )

    @staticmethod
    def test_a_blocked_row_indents_its_note() -> None:
        row = _WORKED.model_copy(
            update={"outcome": "blocked", "unpushed": None, "note": "red:\n1 failed"}
        )

        assert _REPORT.healed(_run(checked=[row])) == (
            "heal — 1 worked\n\n"
            "  #7 feature: blocked, unknown — red:\n      1 failed\n"
        )

    @staticmethod
    def test_a_skipped_row() -> None:
        row = _WORKED.model_copy(update={"outcome": "skipped", "unpushed": None})

        assert "  #7 feature: left alone, unknown\n" in _REPORT.healed(
            _run(checked=[row])
        )

    @staticmethod
    def test_nothing_worked() -> None:
        assert _REPORT.healed(_run()) == "heal — 0 worked\n\n  (none)\n"

    @staticmethod
    def test_what_was_not_reached_and_why() -> None:
        assert _REPORT.healed(_run(queue=[_PULL], stopped="gh died")) == (
            "heal — 0 worked\n\n  (none)\n\n"
            "not reached: feature\n\nthe cast failed: gh died\n"
        )

    @staticmethod
    def test_threads_left_for_you_are_counted() -> None:
        assert _REPORT.healed(_run(surveyed=[_ANSWER])) == (
            "heal — 0 worked\n\n  (none)\n\n"
            "waiting for you, cast with --attended true:\n"
            "  #7 feature: 11 threads\n"
        )

    @staticmethod
    def test_an_attended_cast_leaves_no_threads_waiting() -> None:
        healed = _REPORT.healed(_run(surveyed=[_ANSWER], attended=True))

        assert "waiting" not in healed

    @staticmethod
    def test_a_cast_that_never_answers_leaves_no_threads_waiting() -> None:
        healed = _REPORT.healed(_run(surveyed=[_ANSWER], tasks=["review"]))

        assert "waiting" not in healed

    @staticmethod
    def test_what_was_left_for_the_next_cast() -> None:
        assert _REPORT.healed(_run(queue=[_PULL])) == (
            "heal — 0 worked\n\n  (none)\n\n"
            "out of steps, left for the next cast: feature\n"
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
                        number=5, kind="chore", note="need the metrics"
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
            "  #5 chore/unsized — need the metrics\n"
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


class TestSurveyed:
    @staticmethod
    def test_each_todo_with_what_it_would_work_through() -> None:
        row = Surveyed(
            number=7,
            branch="feature",
            url=_PULL.url,
            todos=["merge", "ci", "answer", "review"],
            red=[Check(name="checks"), Check(name="test")],
            threads=3,
        )

        assert _REPORT.surveyed(row) == (
            "#7 feature: merge, ci (checks, test), answer (3 threads), review"
        )

    @staticmethod
    def test_nothing_to_do_says_so() -> None:
        row = Surveyed(
            number=7, branch="feature", url=_PULL.url, todos=[], red=[], threads=0
        )

        assert _REPORT.surveyed(row) == "#7 feature: nothing to do"

    @staticmethod
    def test_a_branch_that_could_not_be_read_says_why() -> None:
        row = Unsurveyed(number=7, branch="feature", url=_PULL.url, note="gh is down")

        assert _REPORT.surveyed(row) == "#7 feature: could not survey: gh is down"

    @staticmethod
    def test_a_note_on_several_lines_is_indented() -> None:
        row = Unsurveyed(
            number=7, branch="feature", url=_PULL.url, note="fatal:\nno such ref"
        )

        assert _REPORT.surveyed(row) == (
            "#7 feature: could not survey: fatal:\n    no such ref"
        )
