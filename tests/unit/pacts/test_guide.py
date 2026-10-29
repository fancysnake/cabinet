"""What a guide must say."""

import pytest
from pydantic import ValidationError

from cabinet.pacts.guide import Guide


class TestGuide:
    @staticmethod
    @pytest.mark.parametrize("body", ["", " ", "\n\t "])
    def test_a_blank_body_is_refused(body: str) -> None:
        with pytest.raises(ValidationError):
            Guide(body=body)
