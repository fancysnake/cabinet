"""What the report says, on the terminal and on the pull request."""

from cabinet.mills.report import Report
from cabinet.pacts.healing import Checked, Queued, Run, Surveyed, Unsurveyed
from cabinet.pacts.issues import IdentifiedItem, Identifying, Issue, Left, Pinned
from cabinet.pacts.project import Project
from cabinet.pacts.pulls import Check, PullRequest
from cabinet.pacts.threads import (
    ITEM,
    Answer,
    Comment,
    Finding,
    IssueDraft,
    Thread,
    TriageItem,
)
from cabinet.specs import CARD_WIDTH
from tests.conftest import watched

_REPORT = Report()
_PROJECT = Project()


def _ruled(title: str) -> str:
    return title.ljust(CARD_WIDTH, "─")


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
    return Run(project=_PROJECT, attended=False).model_copy(update=update)


class TestHanded:
    @staticmethod
    def test_it_names_the_cast_each_branch_went_to() -> None:
        queued = Queued(pr=_PULL, cast="c1")

        assert _REPORT.handed(_run(queued=[queued])) == (
            "heal — 1 queued\n\n  #7 feature: cast c1\n"
        )

    @staticmethod
    def test_it_says_so_when_it_queued_nothing() -> None:
        assert _REPORT.handed(_run()) == "heal — 0 queued\n\n  (none)\n"

    @staticmethod
    def test_a_cast_the_daemon_left_names_what_it_queued() -> None:
        queued = Queued(pr=_PULL, cast="c1")

        assert _REPORT.handed(_run(queued=[queued], stopped="no daemon")) == (
            "heal — 1 queued\n\n  #7 feature: cast c1\n\nthe cast failed: no daemon\n"
        )


class TestHealed:
    @staticmethod
    def test_a_green_row() -> None:
        assert _REPORT.healed(_run(checked=[_WORKED])) == (
            "heal — 1 worked\n\n  #7 feature: worked, 0 unpushed\n"
        )

    # `heal.main`'s branch where no pull request was opened for it.
    @staticmethod
    def test_a_branch_without_a_pull_request_has_no_number() -> None:
        row = _WORKED.model_copy(update={"number": 0, "branch": "fix/main-abc1234"})

        assert _REPORT.healed(_run(checked=[row])) == (
            "heal — 1 worked\n\n  fix/main-abc1234: worked, 0 unpushed\n"
        )

    @staticmethod
    def test_a_blocked_row_indents_its_note() -> None:
        row = _WORKED.model_copy(
            update={"outcome": "blocked", "unpushed": None, "note": "red:\n1 failed"}
        )

        assert _REPORT.healed(_run(checked=[row])) == (
            "heal — 0 worked\n\n"
            "  #7 feature: blocked, unknown — red:\n      1 failed\n\n"
            "the cast failed: branches blocked: 1\n"
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
            "waiting for you, cast without --unattended:\n"
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
    def test_what_a_cast_out_of_steps_did_not_reach() -> None:
        assert _REPORT.healed(_run(queue=[_PULL])) == (
            "heal — 0 worked\n\n  (none)\n\n"
            "out of steps at this --bound and CI jobs, not reached: feature\n"
        )

    # A pull request the listing never reached looks exactly like one nothing
    # wanted doing to.
    @staticmethod
    def test_a_listing_the_forge_cut_short_says_so() -> None:
        assert _REPORT.healed(_run(truncated=True)) == (
            "heal — 0 worked\n\n  (none)\n\n"
            "the forge listed as many of your open pull requests as it gives at"
            " once: there may be more, and this cast would not have seen them\n"
        )


_ITEM = TriageItem(
    where="src/thing.py:12",
    raised="stop on an empty list",
    left="an empty list crashes the run",
    what="the guard is missing",
    grounds="tested",
    proof="ran it with [] and got IndexError",
    size="small",
    files=1,
    risk="low",
    priority="p1",
    action="fix",
    thread="T1",
)

_THREAD = Thread(
    id="T1",
    resolved=False,
    comments=[Comment(id="1", author="reviewer", body="guard this")],
)


class TestTriage:
    @staticmethod
    def test_every_item_is_a_card_with_its_place_in_the_round() -> None:
        item = _ITEM
        thread = _THREAD
        later = item.model_copy(
            update={
                "thread": "T2",
                "files": 2,
                "priority": "p3",
                "action": "file",
                "left": (
                    "an empty list crashes the run, and the cast that called it"
                    " reports the pull request as answered"
                ),
            }
        )
        quiet = thread.model_copy(update={"id": "T2", "comments": []})

        cards = _REPORT.cards(_PULL, [later, item], [thread, quiet])

        assert cards == [
            (
                item,
                (
                    "#7 Add the thing — thread 1 of 2\n"
                    "\n"
                    f"{_ruled('── The thread ')}\n"
                    "Thread:   src/thing.py:12, raised by reviewer\n"
                    "Raised:   stop on an empty list\n"
                    "If left:  an empty list crashes the run\n"
                    "\n"
                    f"{_ruled('── The reading would FIX it ')}\n"
                    "Action:   fix — the guard is missing\n"
                    "Grounds:  tested — ran it with [] and got IndexError\n"
                    "Estimate: small, 1 file, low risk"
                ),
            ),
            (
                later,
                (
                    "#7 Add the thing — thread 2 of 2\n"
                    "\n"
                    f"{_ruled('── The thread ')}\n"
                    "Thread:   src/thing.py:12\n"
                    "Raised:   stop on an empty list\n"
                    "If left:  an empty list crashes the run, and the cast that"
                    " called it reports the\n"
                    "          pull request as answered\n"
                    "\n"
                    f"{_ruled('── The reading would FILE it ')}\n"
                    "Action:   file — the guard is missing\n"
                    "Grounds:  tested — ran it with [] and got IndexError\n"
                    "Estimate: small, 2 files, low risk"
                ),
            ),
        ]

    # A path broken across two lines cannot be copied.
    @staticmethod
    def test_a_word_longer_than_the_line_stays_whole() -> None:
        path = "src/" + "deep/" * 20 + "thing.py:12"
        item = _ITEM.model_copy(update={"where": path})

        quiet = _THREAD.model_copy(update={"comments": []})

        [(_, card)] = _REPORT.cards(_PULL, [item], [quiet])

        assert f"Thread:   {path}\n" in card

    # `fill` returns nothing for a blank value, which would drop the label.
    @staticmethod
    def test_a_blank_field_still_prints_its_label() -> None:
        item = _ITEM.model_copy(update={"raised": "stop", "left": ""})

        [(_, card)] = _REPORT.cards(_PULL, [item], [_THREAD])

        assert "Raised:   stop\nIf left:\n\n" in card

    # Proof is often a command and its output; joining its lines into one
    # paragraph would lose what it showed.
    @staticmethod
    def test_a_field_of_several_lines_keeps_its_lines() -> None:
        item = _ITEM.model_copy(
            update={"proof": "ran it with []\nTraceback:\n\nIndexError"}
        )

        [(_, card)] = _REPORT.cards(_PULL, [item], [_THREAD])

        assert (
            "Grounds:  tested — ran it with []\n"
            "          Traceback:\n"
            "\n"
            "          IndexError\n"
        ) in card

    @staticmethod
    def test_the_question_names_the_answers_it_takes() -> None:
        asked = _REPORT.asked("the card")

        assert asked.startswith("the card\n\nPress return")
        assert "answer fix, reject\nor file" in asked
        assert asked.endswith("\n->")


class TestDrafted:
    @staticmethod
    def test_the_reply_is_shown_as_it_would_be_posted() -> None:
        thread = _THREAD.model_copy(update={"path": "src/thing.py", "line": 12})
        answer = Answer(thread="T1", reply="Guarded.\n\nThe loop stops first.")

        assert _REPORT.drafted(_PULL, thread, answer, last=False) == (
            f"#{_PULL.number} {_PULL.title} — reply to reviewer — src/thing.py:12\n\n"
            "Guarded.\n\nThe loop stops first.\n\n"
            "Press return or answer ok to post it, or say what to change.\n->"
        )

    @staticmethod
    def test_an_issue_to_file_is_named_above_the_reply() -> None:
        filing = Answer(
            thread="T1", reply="Filed.", issue=IssueDraft(title="Guard it", body="x")
        )

        drafted = _REPORT.drafted(_PULL, _THREAD, filing, last=False)

        assert "reply to reviewer\n\nFiles:    Guard it\n\nFiled.\n" in drafted

    @staticmethod
    def test_the_last_asking_says_what_anything_but_a_return_costs() -> None:
        done = Answer(thread="T1", reply="Done.")

        drafted = _REPORT.drafted(_PULL, _THREAD, done, last=True)

        assert "No redrafts are left at this --bound" in drafted
        assert "say what to change" not in drafted
        assert drafted.endswith("\n->")

    @staticmethod
    def test_a_thread_nobody_wrote_on_is_the_reviews() -> None:
        bare = Thread(id="T1", resolved=False)
        done = Answer(thread="T1", reply="Done.")

        drafted = _REPORT.drafted(_PULL, bare, done, last=False)

        assert drafted.splitlines()[0].endswith("— reply to the review")


class TestFindings:
    # The heading is for whoever opens the pull request and finds a comment on
    # their line; the hidden mark is what `answer` knows the item by.
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
                body=f"## Thermo-nuclear code quality review\n\nguard this\n\n{ITEM}",
            ),
            Finding(
                path="",
                body=(
                    "## Thermo-nuclear code quality review\n\n"
                    f"split the change\n\n{ITEM}"
                ),
            ),
        ]

    @staticmethod
    def test_the_title_follows_the_config() -> None:
        project = _PROJECT.model_copy(update={"review_title": "Night review"})

        headed = _REPORT.findings(project, [Finding(path="", body="hm")])

        assert headed[0].body == f"## Night review\n\nhm\n\n{ITEM}"


_ISSUE = Issue(number=5, title="t", url="https://example.test/5")


class TestIdentify:
    @staticmethod
    def test_every_ending_gets_its_line() -> None:
        identifying = Identifying(
            project=_PROJECT,
            identified=[
                Pinned(
                    item=IdentifiedItem(
                        number=3, kind="feature", size="M", blocked_by=[4]
                    )
                ),
                Pinned(
                    item=IdentifiedItem(
                        number=4,
                        kind="edit",
                        epic=True,
                        children=[12],
                        note="split by layer",
                    ),
                    opened=[10, 11],
                ),
                Pinned(
                    item=IdentifiedItem(number=5, kind="chore", note="need the metrics")
                ),
                Pinned(
                    item=IdentifiedItem(
                        number=6, kind="bug", size="S", blocked_by=[3, 5]
                    ),
                    refused=["could not say #6 is blocked by #3: taken", "gh died"],
                ),
                Left(number=7, outcome="missed"),
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
            " there may be more, and this cast would not have seen them"
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
            identified=[Left(number=2, outcome="stopped")],
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
            todos=["merge", "ci", "review", "answer"],
            red=watched(Check(name="checks", id=1), Check(name="test", id=1)),
            threads=3,
        )

        assert _REPORT.surveyed(row) == (
            "#7 feature: merge, ci (checks, test), review, answer (3 threads)"
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
