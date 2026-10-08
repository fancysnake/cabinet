"""How much of a cast's step budget it speaks for, branch by branch."""

from cabinet.mills.steps import Steps
from cabinet.pacts.project import Project
from cabinet.pacts.pulls import Run
from cabinet.pacts.reviews import Picking, Share
from cabinet.specs import REVIEW_STEPS, SWEEP_STEPS

# A bound of two: `look`, `land`, `settle`, and five `gates`.
_AROUND = 8
_ROUNDS = 2
_STEPS = Steps()


def _picking(reserved: int = 0) -> Picking:
    return Picking(project=Project(), bound=2, batch=7, reserved=reserved)


def _run(reserved: int = 0) -> Run:
    return Run(project=Project(), bound=3, reserved=reserved)


def _rounds(picking: Picking, left: int) -> int:
    share = _STEPS.review_share(picking, left)
    assert share is not None
    return share.rounds


class TestOpening:
    @staticmethod
    def test_queue_up_a_pick_per_branch_the_last_pick_and_recap() -> None:
        branches = 2

        assert _STEPS.opening(branches) == 1 + branches + 1 + 1


class TestReviewShare:
    @staticmethod
    def test_one_round_per_batch() -> None:
        assert [_rounds(_picking(), left) for left in (1, 7, 8, 40)] == [1, 1, 2, 6]

    @staticmethod
    def test_as_many_as_the_budget_reaches() -> None:
        picking = _picking(reserved=REVIEW_STEPS - _AROUND - 4 * _ROUNDS)

        assert _rounds(picking, 40) == _ROUNDS

    @staticmethod
    def test_none_where_a_round_does_not_fit() -> None:
        assert (
            _STEPS.review_share(_picking(reserved=REVIEW_STEPS - _AROUND - 3), 1)
            is None
        )

    @staticmethod
    def test_the_worst_the_rounds_can_spend() -> None:
        assert _STEPS.review_share(_picking(reserved=5), 8) == Share(
            rounds=_ROUNDS, steps=_AROUND + 4 * _ROUNDS
        )


class TestSweepShare:
    # A bound of three: nine steps walked once, four `resolve_conflicts` and
    # seven runs of the gate's loop.
    _WORST = 20

    def test_the_worst_a_branch_can_spend(self) -> None:
        assert _STEPS.sweep_share(_run()) == self._WORST

    def test_a_branch_that_just_fits(self) -> None:
        assert _STEPS.sweep_share(_run(SWEEP_STEPS - self._WORST)) == self._WORST

    def test_none_where_the_branch_does_not_fit(self) -> None:
        assert _STEPS.sweep_share(_run(SWEEP_STEPS - self._WORST + 1)) is None

    @staticmethod
    def test_the_most_the_forge_lists_fits_at_the_default_bound() -> None:
        share = _STEPS.sweep_share(_run())
        assert share is not None

        assert _STEPS.opening(100) + 100 * share == SWEEP_STEPS
