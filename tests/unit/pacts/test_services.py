"""The slot a step reads its services from."""

import pytest

from cabinet.pacts import services as slot
from cabinet.pacts.services import ServicesUnboundError, services


class TestSlot:
    @staticmethod
    def test_nothing_bound_is_named(monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(slot, "_BOUND", [])

        with pytest.raises(ServicesUnboundError, match=r"cabinet\.rituals"):
            services()
