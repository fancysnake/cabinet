"""What a reading of an issue asks the forge for."""

from typing import get_args

import pytest

from cabinet.pacts.issues import EPIC, ISSUE_LABELS, KINDS, SIZES, IdentifiedItem, Kind

# A hex triplet without the hash, the way GitHub takes it.
_HEX = 6


class TestVocabulary:
    # The words the agent is given, the labels `labels:identify` makes and the
    # types a reading may carry are one list, or a cast asks for a label the
    # forge has never been told about.
    @staticmethod
    def test_every_type_size_and_the_epic_label_is_conjured() -> None:
        assert [spec.name for spec in ISSUE_LABELS] == [*KINDS, *SIZES, EPIC]

    @staticmethod
    def test_each_label_says_what_it_means_in_a_colour() -> None:
        assert all(spec.description for spec in ISSUE_LABELS)
        assert all(len(spec.color) == _HEX for spec in ISSUE_LABELS)


class TestWanted:
    @staticmethod
    @pytest.mark.parametrize("kind", get_args(Kind))
    def test_a_sized_issue_asks_for_its_type_and_its_size(kind: Kind) -> None:
        item = IdentifiedItem(number=1, kind=kind, size="M")

        assert item.wanted() == [kind, "M"]

    @staticmethod
    def test_an_epic_asks_for_the_epic_label_in_place_of_a_size() -> None:
        item = IdentifiedItem(number=1, kind="edit", epic=True)

        assert item.wanted() == ["edit", EPIC]

    # An issue nobody could size is not an epic: it wears its type and waits,
    # and the next cast asks about it again.
    @staticmethod
    def test_an_unsized_issue_asks_for_its_type_alone() -> None:
        item = IdentifiedItem(number=1, kind="spike", note="need the metrics first")

        assert item.wanted() == ["spike"]

    # A size alongside `epic` is an answer that contradicts itself, and the
    # epic label is the half that decides: an epic is sized by its parts.
    @staticmethod
    def test_a_size_on_an_epic_is_ignored() -> None:
        item = IdentifiedItem(number=1, kind="feature", size="L", epic=True)

        assert item.wanted() == ["feature", EPIC]
