"""Which calls move to the escalated model."""

import pytest

from cabinet.mills.sizes import Sizes
from cabinet.specs import MANY_CONFLICTS, MANY_RED, MANY_THREADS

_SIZES = Sizes()


class TestEscalates:
    @staticmethod
    def test_a_small_first_attempt_stays() -> None:
        assert not _SIZES.escalates(
            conflicts=MANY_CONFLICTS - 1, red=MANY_RED - 1, threads=MANY_THREADS - 1
        )

    @staticmethod
    @pytest.mark.parametrize(
        ("conflicts", "red", "threads"),
        [(MANY_CONFLICTS, 0, 0), (0, MANY_RED, 0), (0, 0, MANY_THREADS)],
    )
    def test_one_count_at_its_threshold_moves_up(
        conflicts: int, red: int, threads: int
    ) -> None:
        assert _SIZES.escalates(conflicts=conflicts, red=red, threads=threads)

    @staticmethod
    def test_a_retry_moves_up_whatever_the_size() -> None:
        assert _SIZES.escalates(spent=1)
