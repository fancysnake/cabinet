"""What one repository tells the rituals, and the labels that follow from it."""

import tomllib
from pathlib import Path
from typing import get_args

from pydantic import BaseModel

from cabinet.pacts.project import Labels, Marked, Project
from cabinet.pacts.pulls import Mode

# A hex triplet without the hash, the way GitHub takes it.
_HEX = 6

_PAGE = Path(__file__).parents[3] / "docs" / "configuration.md"
_FENCE = "```"


class _Documented(BaseModel):
    cabinet: Project


# The first fenced block on the page is the `[cabinet]` section with every
# default written out.
def _shown() -> str:
    lines = _PAGE.read_text(encoding="utf-8").splitlines()
    opened = lines.index(f"{_FENCE}toml") + 1
    return "\n".join(lines[opened : lines.index(_FENCE, opened)])


# The page and `Project` are two spellings of one set of defaults, and only
# prose asked them to agree. Parsing one into the other is what keeps them in
# step: a default that moves, or a key the page invents, dies here rather than
# in a cast — `extra="forbid"` is what refuses the invented one.
class TestDocumented:
    @staticmethod
    def test_the_configuration_page_shows_the_defaults() -> None:
        assert _Documented.model_validate(tomllib.loads(_shown())).cabinet == Project()


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
