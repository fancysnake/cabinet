"""Which pull requests are taken, and what the check board buys."""

from cabinet.mills.pulls import Pulls
from cabinet.pacts.project import Project
from cabinet.pacts.pulls import Board, Check, PullRequest

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


def _green_board() -> Board:
    return Board(
        checks=[
            Check(name="checks", passed=True),
            Check(name="test", passed=True),
            Check(name="test-postgres", passed=True),
            Check(name="codecov/project", passed=True),
            Check(name="codecov/patch", passed=True, title="100.00% of diff hit"),
        ]
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


class TestWantsCover:
    @staticmethod
    def test_a_green_board_with_a_whole_patch_buys_the_skip() -> None:
        assert not _PULLS.wants_cover(_green_board(), _PROJECT)

    @staticmethod
    def test_a_patch_with_a_gap_wants_cover_even_when_green() -> None:
        board = _green_board()
        board.checks[-1] = Check(
            name="codecov/patch", passed=True, title="96.84% of diff hit (target 96%)"
        )

        assert _PULLS.wants_cover(board, _PROJECT)

    @staticmethod
    def test_a_red_suite_wants_cover() -> None:
        board = _green_board()
        board.checks[1] = Check(name="test", passed=False)

        assert _PULLS.wants_cover(board, _PROJECT)

    @staticmethod
    def test_a_check_still_running_wants_cover() -> None:
        board = _green_board()
        board.checks[3] = Check(name="codecov/project")

        assert _PULLS.wants_cover(board, _PROJECT)

    @staticmethod
    def test_an_empty_board_wants_cover() -> None:
        assert _PULLS.wants_cover(Board(), _PROJECT)

    @staticmethod
    def test_a_short_board_wants_cover() -> None:
        board = _green_board()
        board.truncated = True

        assert _PULLS.wants_cover(board, _PROJECT)

    @staticmethod
    def test_a_patch_with_nothing_to_measure_names_no_gap() -> None:
        board = _green_board()
        board.checks[-1] = Check(
            name="codecov/patch", passed=True, title="Coverage not affected"
        )

        assert not _PULLS.wants_cover(board, _PROJECT)

    @staticmethod
    def test_the_watched_names_are_the_projects() -> None:
        project = Project.model_validate(
            {"ci": {"cover_checks": ["suite"], "patch_check": "patch"}}
        )
        board = Board(checks=[Check(name="suite", passed=True)])

        assert not _PULLS.wants_cover(board, project)
        assert _PULLS.wants_cover(_green_board(), project)


class TestGatesGreen:
    @staticmethod
    def test_green_gate_jobs_are_green() -> None:
        assert _PULLS.gates_green(_green_board(), _PROJECT)

    @staticmethod
    def test_a_red_job_elsewhere_does_not_matter() -> None:
        board = _green_board()
        board.checks[3] = Check(name="codecov/project", passed=False)

        assert _PULLS.gates_green(board, _PROJECT)

    @staticmethod
    def test_a_red_gate_job_is_not_green() -> None:
        board = _green_board()
        board.checks[0] = Check(name="checks", passed=False)

        assert not _PULLS.gates_green(board, _PROJECT)

    @staticmethod
    def test_silence_is_not_green() -> None:
        assert not _PULLS.gates_green(Board(), _PROJECT)

    @staticmethod
    def test_a_running_job_is_not_green() -> None:
        board = _green_board()
        board.checks[2] = Check(name="test-postgres")

        assert not _PULLS.gates_green(board, _PROJECT)

    @staticmethod
    def test_a_short_board_is_not_green() -> None:
        board = _green_board()
        board.truncated = True

        assert not _PULLS.gates_green(board, _PROJECT)
