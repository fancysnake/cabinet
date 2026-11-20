"""How much of a cast's step budget it speaks for, branch by branch."""

from cabinet.mills.steps import Steps
from cabinet.pacts.healing import Run
from cabinet.pacts.project import Project
from cabinet.specs import HEAL_STEPS

_STEPS = Steps()


def _run(reserved: int = 0) -> Run:
    return Run(attended=True, project=Project(), bound=3, reserved=reserved)


class TestOpening:
    @staticmethod
    def test_the_muster_a_survey_per_branch_the_last_survey_and_chart() -> None:
        branches = 2

        assert _STEPS.opening(branches) == 1 + branches + 1 + 1


class TestHealShare:
    # A bound of three: fifteen steps walked once, four `resolve_conflicts`,
    # seven runs of the gate's loop, ten for each of the three default jobs
    # plus the `pick_job` that finds none left, and twenty-five for `answer`.
    _WORST = 82

    def test_the_worst_a_branch_can_spend(self) -> None:
        assert _STEPS.heal_share(_run()) == self._WORST

    def test_a_branch_that_just_fits(self) -> None:
        assert _STEPS.heal_share(_run(HEAL_STEPS - self._WORST)) == self._WORST

    def test_none_where_the_branch_does_not_fit(self) -> None:
        assert _STEPS.heal_share(_run(HEAL_STEPS - self._WORST + 1)) is None

    # A cast that works a branch works one, with the steps around it spoken
    # for first.
    @staticmethod
    def test_one_branch_fits_at_the_default_bound() -> None:
        assert _STEPS.heal_share(_run(_STEPS.opening(1))) is not None

    # `heal.mine` on the thousand pull requests GitHub lists: every step
    # `opening` counts, and `attend`.
    @staticmethod
    def test_the_most_the_forge_lists_fits() -> None:
        assert _STEPS.opening(1000) + 1 == HEAL_STEPS
