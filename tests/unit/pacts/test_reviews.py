"""A branch taken out of the cast, and the rounds it spends."""

from cabinet.pacts.project import Project
from cabinet.pacts.pulls import PullRequest
from cabinet.pacts.reviews import Branch, Picking, Share

_PULL = PullRequest(
    number=7,
    title="pr 7",
    url="https://github.com/o/r/pull/7",
    branch="feature",
    base="main",
    updated_at="2026-08-01T22:00:00Z",
)


def _picking(reserved: int = 0) -> Picking:
    return Picking(project=Project(), bound=2, reserved=reserved)


class TestTake:
    @staticmethod
    def test_the_share_is_given_and_spoken_for() -> None:
        taken = _picking(reserved=5).take(_PULL, Share(rounds=2, steps=16))

        assert taken == Branch(
            picking=_picking(reserved=21), name="feature", number=7, rounds=2
        )


class TestTaken:
    @staticmethod
    def test_a_round_taken_is_one_fewer_left() -> None:
        branch = Branch(picking=_picking(), name="feature", number=7, rounds=2)

        assert branch.taken(3).rounds == 1
