"""What one repository tells the rituals, and the labels that follow from it."""

import tomllib
from pathlib import Path

import pytest
from pydantic import BaseModel, ValidationError

from cabinet.pacts.project import Ci, CiJob, Labels, Project

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


class TestConjured:
    @staticmethod
    def test_every_label_heal_touches_with_the_defaults() -> None:
        assert [spec.name for spec in Labels().conjured()] == [
            "pr::thermo",
            "pr::wait",
            "v:guide:done",
            "v:answer:done",
        ]

    @staticmethod
    def test_the_names_follow_the_config() -> None:
        labels = Labels(
            reviewed="cabinet::reviewed", wait="hold", qa="qa", answered="said"
        )

        assert [spec.name for spec in labels.conjured()] == [
            "cabinet::reviewed",
            "hold",
            "qa",
            "said",
        ]

    @staticmethod
    def test_each_label_says_what_it_means() -> None:
        reviewed, wait, qa, answered = Labels().conjured()

        assert "remove to ask again" in reviewed.description
        assert "Hands off" in wait.description
        assert "guide was posted" in qa.description
        assert "answered" in answered.description
        assert all(len(spec.color) == _HEX for spec in Labels().conjured())


class TestLongTasks:
    @staticmethod
    def test_the_rituals_own_first_then_the_projects() -> None:
        project = Project.model_validate(
            {"agent": {"may_not_run": ["mise run test:e2e"]}}
        )

        assert project.long_tasks() == [
            "mise run pr-fix",
            "mise run diff-cover",
            "mise run test:py:cov:diff",
            "mise run test:e2e",
        ]

    # A repository whose two measurements are one command, like this one.
    @staticmethod
    def test_a_command_named_twice_is_listed_once() -> None:
        same = "mise run test:py:cov:diff"
        project = Project(coverage=same, fast_coverage=same)

        assert project.long_tasks().count(same) == 1


class TestCiJobs:
    @staticmethod
    def test_a_check_belongs_to_the_job_its_name_starts_with() -> None:
        assert Project().ci.job("test-postgres") == CiJob()

    @staticmethod
    def test_the_longest_key_wins() -> None:
        ci = Ci.model_validate(
            {"jobs": {"codecov/": {}, "codecov/patch": {"covering": True}}}
        )

        assert ci.covering("codecov/patch")
        assert not ci.covering("codecov/project")

    @staticmethod
    def test_a_check_no_key_matches_has_no_job() -> None:
        assert Project().ci.job("docs") is None
        assert not Project().ci.covering("docs")

    @staticmethod
    def test_a_job_refuses_a_key_it_does_not_know() -> None:
        with pytest.raises(ValidationError):
            CiJob.model_validate({"cover": True})
