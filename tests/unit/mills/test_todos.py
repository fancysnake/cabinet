"""What a pull request needs next: facts make a todo, labels only take one away."""

from cabinet.mills.todos import Todos
from cabinet.pacts.healing import Facts, Surveyed, Todo
from cabinet.pacts.project import Project
from cabinet.pacts.pulls import Board, Check, PullRequest
from cabinet.pacts.threads import Thread

_TODOS = Todos()
_PROJECT = Project()
_DONE = ["pr::thermo", "v:guide:done"]


def _facts(
    *,
    labels: list[str] | None = None,
    checks: list[Check] | None = None,
    threads: list[Thread] | None = None,
    conflicted: bool = False,
) -> Facts:
    pull = PullRequest(
        number=7,
        title="pr 7",
        url="https://example.test/pull/7",
        branch="feature",
        base="main",
        updated_at="2026-08-01T00:00:00Z",
        labels=["pr::thermo"] if labels is None else labels,
    )
    return Facts(
        pull=pull,
        board=Board(checks=checks or []),
        threads=threads or [],
        conflicted=conflicted,
    )


def _todos(facts: Facts) -> list[Todo]:
    return _TODOS.surveyed(facts, _PROJECT).todos


def _red(board: Board, project: Project) -> list[str]:
    row = _TODOS.surveyed(_facts().model_copy(update={"board": board}), project)
    return [check.name for check in row.red]


class TestTodos:
    @staticmethod
    def test_a_conflict_is_a_merge() -> None:
        assert _todos(_facts(conflicted=True)) == ["merge"]

    @staticmethod
    def test_a_red_configured_job_is_ci() -> None:
        facts = _facts(checks=[Check(name="test-postgres", passed=False)])

        assert _todos(facts) == ["ci"]

    @staticmethod
    def test_an_unresolved_thread_is_an_answer() -> None:
        facts = _facts(threads=[Thread(id="1", resolved=False)])

        assert _todos(facts) == ["answer"]

    @staticmethod
    def test_an_unreviewed_branch_is_a_review() -> None:
        assert _todos(_facts(labels=["v:guide:done"])) == ["review"]

    @staticmethod
    def test_nothing_else_to_do_is_a_guide() -> None:
        assert _todos(_facts()) == ["guide"]

    @staticmethod
    def test_guide_waits_for_everything_else() -> None:
        facts = _facts(labels=[], threads=[Thread(id="1", resolved=False)])

        assert _todos(facts) == ["answer", "review"]

    @staticmethod
    def test_the_qa_label_takes_the_guide_away() -> None:
        assert not _todos(_facts(labels=_DONE))

    @staticmethod
    def test_every_todo_in_the_order_a_cast_works_them() -> None:
        facts = _facts(
            labels=[],
            checks=[Check(name="checks", passed=False)],
            threads=[Thread(id="1", resolved=False)],
            conflicted=True,
        )

        assert _todos(facts) == ["merge", "ci", "answer", "review"]

    # Labels only stop a repeat: the same facts under any label are the same
    # todos or fewer.
    @staticmethod
    def test_no_label_adds_a_todo() -> None:
        labels = [*_DONE, "pr::wait", "v:merge:started", "v:merge:done"]

        assert not _todos(_facts(labels=labels))

    @staticmethod
    def test_a_branch_behind_its_base_is_not_a_merge() -> None:
        assert "merge" not in _todos(_facts(conflicted=False))

    @staticmethod
    def test_a_resolved_thread_is_not_an_answer() -> None:
        facts = _facts(labels=_DONE, threads=[Thread(id="1", resolved=True)])

        assert not _todos(facts)


class TestRed:
    @staticmethod
    def test_only_configured_jobs_count() -> None:
        board = Board(
            checks=[
                Check(name="checks", passed=False),
                Check(name="docs", passed=False),
                Check(name="test", passed=True),
            ]
        )

        assert _red(board, _PROJECT) == ["checks"]

    @staticmethod
    def test_a_running_check_is_not_red() -> None:
        assert not _red(Board(checks=[Check(name="checks")]), _PROJECT)

    @staticmethod
    def test_a_check_named_twice_is_named_once() -> None:
        red = Check(name="test", passed=False)

        assert _red(Board(checks=[red, red]), _PROJECT) == ["test"]

    @staticmethod
    def test_the_jobs_are_the_projects() -> None:
        project = Project.model_validate({"ci": {"jobs": {"docs": {}}}})
        board = Board(
            checks=[Check(name="docs", passed=False), Check(name="test", passed=False)]
        )

        assert _red(board, project) == ["docs"]

    @staticmethod
    def test_a_green_patch_naming_a_gap_is_red() -> None:
        patch = Check(name="codecov/patch", passed=True, title="96.84% of diff hit")

        assert _red(Board(checks=[patch]), _PROJECT) == ["codecov/patch"]

    @staticmethod
    def test_a_whole_patch_is_not_red() -> None:
        patch = Check(name="codecov/patch", passed=True, title="100.00% of diff hit")

        assert not _red(Board(checks=[patch]), _PROJECT)

    @staticmethod
    def test_a_patch_with_nothing_to_measure_names_no_gap() -> None:
        patch = Check(name="codecov/patch", passed=True, title="Coverage not affected")

        assert not _red(Board(checks=[patch]), _PROJECT)

    @staticmethod
    def test_only_a_covering_job_names_a_gap() -> None:
        suite = Check(name="test", passed=True, title="96.84% of diff hit")

        assert not _red(Board(checks=[suite]), _PROJECT)


class TestSurveyed:
    @staticmethod
    def test_the_row_says_what_ci_and_answer_would_work_through() -> None:
        facts = _facts(
            checks=[Check(name="checks", passed=False)],
            threads=[Thread(id="1", resolved=False), Thread(id="2", resolved=True)],
        )

        assert _TODOS.surveyed(facts, _PROJECT) == Surveyed(
            number=7,
            branch="feature",
            url="https://example.test/pull/7",
            todos=["ci", "answer"],
            red=[Check(name="checks", passed=False)],
            threads=1,
        )
