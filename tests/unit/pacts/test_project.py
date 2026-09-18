"""What one repository tells the rituals, and the labels that follow from it."""

from typing import get_args

from cabinet.pacts.project import Labels, Marked
from cabinet.pacts.pulls import Mode

# A hex triplet without the hash, the way GitHub takes it.
_HEX = 6


# `Mode` says it is a narrowing of `Marked` and no type can hold it to that:
# a pass is also the name of the checkpoint it marks, so a pass whose name is
# not in `Marked` would mark a label `labels` never made.
class TestMarked:
    @staticmethod
    def test_every_pass_is_a_ritual_that_marks() -> None:
        assert set(get_args(Mode)) <= set(get_args(Marked))


class TestConjured:
    @staticmethod
    def test_every_label_the_rituals_touch_with_the_defaults() -> None:
        assert [spec.name for spec in Labels().conjured()] == [
            "pr::thermo",
            "pr::wait",
            "v:refresh:started",
            "v:refresh:done",
            "v:cover:started",
            "v:cover:done",
            "v:review:started",
            "v:review:done",
        ]

    @staticmethod
    def test_the_names_follow_the_config() -> None:
        labels = Labels(reviewed="cabinet::reviewed", wait="hold", marker="c")

        names = [spec.name for spec in labels.conjured()]

        assert names[:2] == ["cabinet::reviewed", "hold"]
        assert names[2] == "c:refresh:started"

    @staticmethod
    def test_each_label_says_what_it_means() -> None:
        reviewed, wait, started, *_ = Labels().conjured()

        assert "remove to ask again" in reviewed.description
        assert "Hands off" in wait.description
        assert (
            started.description == "refresh began on this branch and has not finished"
        )
        assert all(len(spec.color) == _HEX for spec in Labels().conjured())
