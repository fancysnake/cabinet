"""What one round of a repair loop comes to, on whichever loop is asking."""

from cabinet.mills.prompts import Prompts
from cabinet.mills.repairs import Repairs
from cabinet.mills.verdicts import Verdicts
from cabinet.pacts.project import Project
from cabinet.pacts.repairs import Attempt, Fixed, Repair, Stalled
from cabinet.pacts.tasks import Ran

_PROJECT = Project()
_REPAIRS = Repairs(Prompts(), Verdicts())

# The same bound every test starts from, so a spend can be read against it.
_BOUND = 3

_MISSING = """Diff Coverage
Diff: main...HEAD
-------------
src/thing.py (80.0%): Missing lines 12-14
-------------
Total:   10 lines
Missing: 3 lines
-------------
"""
_CLEAN = _MISSING.replace("src/thing.py (80.0%): Missing lines 12-14\n", "").replace(
    "Missing: 3 lines", "Missing: 0 lines"
)


def _red(stdout: str = "", stderr: str = "") -> Ran:
    return Ran(stdout=stdout, stderr=stderr, exit_code=1)


def _green(stdout: str = "") -> Ran:
    return Ran(stdout=stdout, stderr="", exit_code=0)


# The gate a loop owes green follows what it is measuring, and defaults to the
# whole of it: `gate` is only named where the round is a narrow one.
def _attempt(
    ran: Ran,
    *,
    gate: str = "",
    spent: int = 0,
    seen: list[str] | None = None,
    covering: bool = False,
) -> Attempt:
    whole = _PROJECT.coverage if covering else _PROJECT.gate
    return Attempt(
        project=_PROJECT,
        ran=ran,
        gate=gate or whole,
        whole=whole,
        spent=spent,
        bound=_BOUND,
        seen=seen or [],
        covering=covering,
    )


class TestGreen:
    @staticmethod
    def test_the_whole_gate_passing_is_the_whole_gate() -> None:
        assert _REPAIRS.ruling(_attempt(_green())) == Fixed(whole=True)

    # A task passing on its own is the reason to spend the gate, not the gate
    # passing.
    @staticmethod
    def test_a_narrow_task_passing_is_not() -> None:
        ruling = _REPAIRS.ruling(_attempt(_green(), gate="mise run lint:ruff"))

        assert ruling == Fixed(whole=False)

    # The coverage task names missing lines and still exits 0, so the exit
    # code is only half the answer.
    @staticmethod
    def test_a_clean_report_is_green() -> None:
        ruling = _REPAIRS.ruling(_attempt(_green(_CLEAN), covering=True))

        assert ruling == Fixed(whole=True)

    @staticmethod
    def test_a_report_naming_missing_lines_is_not_green() -> None:
        ruling = _REPAIRS.ruling(_attempt(_green(_MISSING), covering=True))

        assert isinstance(ruling, Repair)


class TestSpending:
    @staticmethod
    def test_a_red_gate_buys_a_repair_against_the_task_that_broke() -> None:
        ran = _red("E501 too long", "[lint:ruff] ERROR task failed")

        ruling = _REPAIRS.ruling(_attempt(ran))

        assert isinstance(ruling, Repair)
        assert ruling.next_gate == "mise run lint:ruff"
        assert "E501 too long" in ruling.asking
        assert ruling.seen == ["E501 too long"]
        assert "as you decided" in ruling.declined

    # Lines are re-measured without the slow suites: what an agent writes for
    # a gap is a test, and the fast suite is the one that runs it.
    @staticmethod
    def test_missing_lines_buy_a_test_and_the_fast_measurement() -> None:
        ruling = _REPAIRS.ruling(_attempt(_green(_MISSING), covering=True))

        assert isinstance(ruling, Repair)
        assert ruling.next_gate == _PROJECT.fast_coverage
        assert _MISSING in ruling.asking
        assert "leaves the slow suites out" not in ruling.asking

    @staticmethod
    def test_a_partial_measurement_says_what_it_cannot_see() -> None:
        ruling = _REPAIRS.ruling(
            _attempt(_green(_MISSING), gate=_PROJECT.fast_coverage, covering=True)
        )

        assert isinstance(ruling, Repair)
        assert "leaves the slow suites out" in ruling.asking

    # A suite that will not run at all is repaired like any other red gate,
    # and falls back to the fast measurement where the runner named nothing.
    @staticmethod
    def test_a_red_suite_under_coverage_is_repaired_as_a_gate() -> None:
        ruling = _REPAIRS.ruling(_attempt(_red("1 failed"), covering=True))

        assert isinstance(ruling, Repair)
        assert ruling.next_gate == _PROJECT.fast_coverage
        assert ruling.asking.startswith("`mise run diff-cover` is this project's gate")


class TestStalling:
    @staticmethod
    def test_a_spent_budget_stands_down_and_remembers() -> None:
        ruling = _REPAIRS.ruling(_attempt(_red("1 failed"), spent=_BOUND))

        assert ruling == Stalled(
            reason="`mise run pr-fix` is still red:\n1 failed", seen=["1 failed"]
        )

    # What lines a branch left uncovered is that branch's own business: two
    # branches missing lines in the same file look identical from here.
    @staticmethod
    def test_missing_lines_are_not_remembered() -> None:
        ruling = _REPAIRS.ruling(
            _attempt(_green(_MISSING), spent=_BOUND, covering=True)
        )

        assert isinstance(ruling, Stalled)
        assert "still reports missing lines" in ruling.reason
        assert not ruling.seen

    @staticmethod
    def test_a_verdict_the_run_gave_up_on_is_not_paid_for_twice() -> None:
        ruling = _REPAIRS.ruling(
            _attempt(_red("1 failed in 2s"), seen=["1 failed in 9s"])
        )

        assert ruling == Stalled(
            reason="`mise run pr-fix` is red as it already was:\n1 failed in 2s",
            seen=["1 failed in 9s"],
        )

    # Asked before the first repair and not after, so this reads "the branch
    # arrived broken the same way", never "the agent failed to fix it twice".
    @staticmethod
    def test_a_round_that_has_already_spent_is_not_read_against_the_memory() -> None:
        ruling = _REPAIRS.ruling(
            _attempt(_red("1 failed in 2s"), spent=1, seen=["1 failed in 9s"])
        )

        assert isinstance(ruling, Repair)
