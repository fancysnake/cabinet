"""The components a heal cast takes from the command line."""

import pytest
from pydantic import ValidationError

from cabinet.pacts.healing import Heal, HealPr


class TestHeal:
    @staticmethod
    def test_an_unknown_key_is_refused() -> None:
        with pytest.raises(ValidationError):
            Heal.model_validate({"attended": False})

    @staticmethod
    def test_an_unknown_key_is_refused_for_one_pull_request() -> None:
        with pytest.raises(ValidationError):
            HealPr.model_validate({"number": 7, "attended": False})
