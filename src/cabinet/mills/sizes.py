"""When a problem is too much for a job's first-choice model."""

from typing_extensions import override

from cabinet.pacts.services import SizesProtocol
from cabinet.specs import MANY_CONFLICTS, MANY_RED, MANY_THREADS


class Sizes(SizesProtocol):
    # A spent attempt escalates whatever the size: the first one did not take,
    # so the root cause is unclear.
    @override
    def escalates(
        self, *, conflicts: int = 0, red: int = 0, threads: int = 0, spent: int = 0
    ) -> bool:
        return (
            spent > 0
            or conflicts >= MANY_CONFLICTS
            or red >= MANY_RED
            or threads >= MANY_THREADS
        )
