"""What the ritual hands on from a task it ran."""

from cabinet.mills.verdicts import Verdicts, same_verdict
from cabinet.pacts.tasks import Ran
from cabinet.specs import BUDGET, VERDICT_LINES

# Ten characters once its newline is counted, so a whole number of these is
# exactly the budget and the boundary can be named rather than approached.
_ROW = "x" * 9
_FITS = BUDGET // 10

_REPORT = """Diff Coverage
Diff: main...HEAD
-------------
src/thing.py (80.0%): Missing lines 12-14
-------------
Total:   10 lines
Missing: 5 lines
Coverage: 50%
-------------
"""

_VERDICTS = Verdicts()


def _ran(*, stdout: str = "", stderr: str = "") -> Ran:
    return Ran(stdout=stdout, stderr=stderr, exit_code=1)


def _rows(count: int) -> str:
    return "\n".join([_ROW] * count)


class TestSaid:
    @staticmethod
    def test_both_streams_are_kept() -> None:
        assert _VERDICTS.said(_ran(stdout="E501 too long", stderr="1 failed")) == (
            "E501 too long\n1 failed"
        )

    # The agent pays for what it reads, and a cursor move is not worth a token.
    @staticmethod
    def test_colour_and_cursor_moves_are_stripped() -> None:
        coloured = "\x1b[1A\x1b[2K\x1b[31m1 failed\x1b[39m"

        assert _VERDICTS.said(_ran(stdout=coloured)) == "1 failed"

    @staticmethod
    def test_a_trailing_newline_is_not_a_line() -> None:
        assert _VERDICTS.said(_ran(stdout="E501 too long\n", stderr="1 failed\n")) == (
            "E501 too long\n1 failed"
        )

    @staticmethod
    def test_a_log_that_fits_the_budget_comes_back_whole() -> None:
        fits = _rows(_FITS)

        assert _VERDICTS.said(_ran(stdout=fits)) == fits

    @staticmethod
    def test_one_line_over_the_budget_drops_exactly_one() -> None:
        over = _rows(_FITS + 1)

        trimmed = _VERDICTS.said(_ran(stdout=over))

        assert trimmed == f"[1 earlier lines omitted]\n{_rows(_FITS)}"

    @staticmethod
    def test_a_long_log_keeps_its_tail_and_says_what_it_dropped() -> None:
        run = "\n".join(
            [f"tests/test_{index}.py PASSED" for index in range(_FITS)] + ["1 failed"]
        )

        trimmed = _VERDICTS.said(_ran(stdout=run))

        assert trimmed.startswith("[")
        assert trimmed.endswith("1 failed")
        assert "tests/test_0.py PASSED" not in trimmed

    # A single line longer than the budget is still the whole verdict.
    @staticmethod
    def test_the_last_line_is_kept_whether_it_fits_or_not() -> None:
        wide = "y" * (BUDGET * 2)

        assert _VERDICTS.said(_ran(stdout=f"first\n{wide}")) == (
            f"[1 earlier lines omitted]\n{wide}"
        )

    @staticmethod
    def test_each_stream_gets_its_own_budget() -> None:
        trimmed = _VERDICTS.said(_ran(stdout=_rows(_FITS), stderr=_rows(_FITS)))

        assert trimmed == f"{_rows(_FITS)}\n{_rows(_FITS)}"


class TestVerdict:
    @staticmethod
    def test_the_last_dozen_lines_of_stdout() -> None:
        lines = [f"line {index}" for index in range(VERDICT_LINES + 3)]

        assert _VERDICTS.verdict(_ran(stdout="\n".join(lines))) == "\n".join(
            lines[-VERDICT_LINES:]
        )

    @staticmethod
    def test_stderr_only_where_stdout_said_nothing() -> None:
        assert _VERDICTS.verdict(_ran(stdout="  \n", stderr="boom")) == "boom"

    @staticmethod
    def test_stderr_is_ignored_where_stdout_spoke() -> None:
        assert _VERDICTS.verdict(_ran(stdout="1 failed", stderr="chatter")) == (
            "1 failed"
        )

    @staticmethod
    def test_blank_lines_are_not_lines() -> None:
        assert _VERDICTS.verdict(_ran(stdout="a\n\n\n  \nb")) == "a\nb"

    @staticmethod
    def test_colour_is_stripped() -> None:
        assert _VERDICTS.verdict(_ran(stdout="\x1b[31m1 failed\x1b[0m")) == "1 failed"


class TestSameVerdict:
    @staticmethod
    def test_digits_do_not_tell_two_runs_apart() -> None:
        assert same_verdict("1 failed in 3.21s", "1 failed in 4.02s")

    @staticmethod
    def test_a_different_failure_is_different() -> None:
        assert not same_verdict("test_a failed", "test_b failed")

    @staticmethod
    def test_an_empty_verdict_matches_nothing() -> None:
        assert not same_verdict("", "")


class TestAlreadySeen:
    @staticmethod
    def test_recognised_anywhere_in_the_list() -> None:
        assert _VERDICTS.already_seen("1 failed in 2s", ["x", "1 failed in 9s"])

    @staticmethod
    def test_not_recognised_where_nothing_matches() -> None:
        assert not _VERDICTS.already_seen("1 failed", ["2 errors"])

    @staticmethod
    def test_an_empty_list_recognises_nothing() -> None:
        assert not _VERDICTS.already_seen("1 failed", [])


class TestCoverageReport:
    @staticmethod
    def test_the_report_from_its_banner_on() -> None:
        ran = _ran(stdout=f"tests/test_x.py PASSED\n{_REPORT}")

        assert _VERDICTS.coverage_report(ran) == _REPORT

    @staticmethod
    def test_the_trimmed_log_where_no_report_was_printed() -> None:
        ran = _ran(stdout="no coverage data", stderr="boom")

        assert _VERDICTS.coverage_report(ran) == "no coverage data\nboom"


class TestNarrowed:
    @staticmethod
    def test_the_first_failed_task_is_named() -> None:
        ran = _ran(
            stderr=(
                "[lint:mypy] ERROR task failed\n[lint:py] ERROR task failed\n"
                "[pr-fix] ERROR task failed"
            )
        )

        assert _VERDICTS.narrowed(ran) == "mise run lint:mypy"

    @staticmethod
    def test_stdout_is_read_first() -> None:
        ran = _ran(
            stdout="[test:unit] ERROR task failed", stderr="[lint:py] ERROR task failed"
        )

        assert _VERDICTS.narrowed(ran) == "mise run test:unit"

    @staticmethod
    def test_empty_where_mise_named_nothing() -> None:
        assert not _VERDICTS.narrowed(_ran(stdout="1 failed"))

    @staticmethod
    def test_colour_does_not_hide_the_name() -> None:
        ran = _ran(stderr="\x1b[31m[lint:ruff] ERROR task failed\x1b[0m")

        assert _VERDICTS.narrowed(ran) == "mise run lint:ruff"

    @staticmethod
    def test_a_dotted_task_name_is_read_whole() -> None:
        ran = _ran(stderr="[test:py.cov-diff] ERROR task failed")

        assert _VERDICTS.narrowed(ran) == "mise run test:py.cov-diff"
