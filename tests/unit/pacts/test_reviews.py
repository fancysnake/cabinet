"""How much of the step budget a branch may take, and what it is charged."""

from cabinet.pacts.project import Project
from cabinet.pacts.reviews import STEPS, Branch, Picking

# A bound of two: `look`, the last `read`, `land`, `settle`, and five `gates`.
_AROUND = 9
_ROUNDS = 2


def _picking(reserved: int = 0) -> Picking:
    return Picking(project=Project(), bound=2, batch=7, reserved=reserved)


class TestRoundsFor:
    @staticmethod
    def test_one_round_per_batch() -> None:
        assert [_picking().rounds_for(left) for left in (1, 7, 8, 40)] == [1, 1, 2, 6]

    @staticmethod
    def test_as_many_as_the_budget_reaches() -> None:
        picking = _picking(reserved=STEPS - _AROUND - 4 * _ROUNDS)

        assert picking.rounds_for(40) == _ROUNDS

    @staticmethod
    def test_none_where_a_round_does_not_fit() -> None:
        assert not _picking(reserved=STEPS - _AROUND - 3).rounds_for(1)


class TestGiven:
    @staticmethod
    def test_the_worst_the_rounds_can_spend_is_reserved() -> None:
        branch = Branch(picking=_picking(reserved=5), name="feature", number=7)

        given = branch.given(_ROUNDS)

        assert given.rounds == _ROUNDS
        assert given.picking.reserved == 5 + _AROUND + 4 * _ROUNDS

    @staticmethod
    def test_a_round_taken_is_one_fewer_left() -> None:
        branch = Branch(picking=_picking(), name="feature", number=7).given(2)

        assert branch.taken(3).rounds == 1
