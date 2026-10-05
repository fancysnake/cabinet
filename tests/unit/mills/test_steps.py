"""How much of `review`'s step budget a cast speaks for, branch by branch."""

from cabinet.mills.steps import Steps
from cabinet.pacts.project import Project
from cabinet.pacts.reviews import Picking, Share
from cabinet.specs import STEPS

# A bound of two: `look`, `land`, `settle`, and five `gates`.
_AROUND = 8
_ROUNDS = 2
_STEPS = Steps()


def _picking(reserved: int = 0) -> Picking:
    return Picking(project=Project(), bound=2, batch=7, reserved=reserved)


def _rounds(picking: Picking, left: int) -> int:
    share = _STEPS.share(picking, left)
    assert share is not None
    return share.rounds


class TestOpening:
    @staticmethod
    def test_queue_up_a_pick_per_branch_the_last_pick_and_recap() -> None:
        branches = 2

        assert _STEPS.opening(branches) == 1 + branches + 1 + 1


class TestShare:
    @staticmethod
    def test_one_round_per_batch() -> None:
        assert [_rounds(_picking(), left) for left in (1, 7, 8, 40)] == [1, 1, 2, 6]

    @staticmethod
    def test_as_many_as_the_budget_reaches() -> None:
        picking = _picking(reserved=STEPS - _AROUND - 4 * _ROUNDS)

        assert _rounds(picking, 40) == _ROUNDS

    @staticmethod
    def test_none_where_a_round_does_not_fit() -> None:
        assert _STEPS.share(_picking(reserved=STEPS - _AROUND - 3), 1) is None

    @staticmethod
    def test_the_worst_the_rounds_can_spend() -> None:
        assert _STEPS.share(_picking(reserved=5), 8) == Share(
            rounds=_ROUNDS, steps=_AROUND + 4 * _ROUNDS
        )
