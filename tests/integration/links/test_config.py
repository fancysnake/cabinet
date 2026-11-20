"""The `[cabinet]` table, merged by vekna across the places it reads config."""

from pathlib import Path

import pytest
from vekna.lexicon import RitualDefinitionError

from cabinet.links.config.vekna_toml import read_project
from cabinet.pacts.project import HEAL_NEEDS, IDENTIFY_NEEDS, ConfigError, Project

_SECTION = """\
[rituals]
modules = ["cabinet.rituals"]

[cabinet]
forge = "gitlab"
gate = "mise run check"
sign_commits = false

[cabinet.labels]
wait = "hold"

[cabinet.agent]
may_not_run = ["mise run test:e2e"]
"""


class TestReadProject:
    @staticmethod
    def test_the_section_is_read_and_the_rest_is_ignored(here: Path) -> None:
        (here / ".vekna.toml").write_text(_SECTION)

        project = read_project(HEAL_NEEDS)

        assert project.forge == "gitlab"
        assert project.gate == "mise run check"
        assert project.sign_commits is False
        assert project.labels.wait == "hold"
        assert project.labels.reviewed == "pr::thermo"
        assert project.agent.may_not_run == ["mise run test:e2e"]

    @staticmethod
    def test_found_by_walking_up(here: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        (here / ".vekna.toml").write_text(_SECTION)
        nested = here / "src" / "pkg"
        nested.mkdir(parents=True)
        monkeypatch.chdir(nested)

        assert read_project(HEAL_NEEDS).forge == "gitlab"

    @staticmethod
    @pytest.mark.usefixtures("here")
    def test_a_file_without_the_section_means_the_defaults() -> None:
        assert read_project(HEAL_NEEDS) == Project()

    @staticmethod
    def test_a_project_with_no_file_reads_the_user_config(
        tmp_path: Path, user_config: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(tmp_path)
        user_config.write_text(
            f'[projects.mine]\npath = "{tmp_path}"\n\n'
            '[projects.mine.cabinet]\ngate = "mise run check"\n',
            encoding="utf-8",
        )

        assert read_project(HEAL_NEEDS).gate == "mise run check"

    # Key by key, the project's file and the user's table for the project both
    # beat what the user sets for every project. Which of those two wins is
    # vekna's to say and differs between its versions, so no key is set in both.
    @staticmethod
    def test_the_nearest_place_wins_each_key(here: Path, user_config: Path) -> None:
        (here / ".vekna.toml").write_text(
            '[cabinet]\ngate = "from the file"\nbase = "from the file"\n'
        )
        user_config.write_text(
            '[cabinet]\nbase = "for every project"\nremote = "for every project"\n'
            'review_title = "for every project"\n\n'
            f'[projects.mine]\npath = "{here}"\n\n'
            '[projects.mine.cabinet]\nremote = "for this project"\n'
            'fast_coverage = "for this project"\n',
            encoding="utf-8",
        )

        project = read_project(HEAL_NEEDS)

        assert project.gate == "from the file"
        assert project.base == "from the file"
        assert project.remote == "for this project"
        assert project.fast_coverage == "for this project"
        assert project.review_title == "for every project"

    @staticmethod
    def test_a_refused_value_names_where_it_was_set(here: Path) -> None:
        (here / ".vekna.toml").write_text('[cabinet]\nforge = "sourcehut"\n')

        with pytest.raises(ConfigError, match=r"(?s)\.vekna\.toml: \[cabinet\].*forge"):
            read_project(HEAL_NEEDS)

    @staticmethod
    def test_a_value_only_another_ritual_reads_is_not_checked(here: Path) -> None:
        (here / ".vekna.toml").write_text("[cabinet]\nidentify_skill = 7\n")

        assert read_project(HEAL_NEEDS) == Project()
        with pytest.raises(ConfigError, match="identify_skill"):
            read_project(IDENTIFY_NEEDS)

    # Refused for every ritual: it may be a needed key misspelt.
    @staticmethod
    def test_a_typo_dies_at_the_boundary(here: Path) -> None:
        (here / ".vekna.toml").write_text('[cabinet]\ngates = "mise run x"\n')

        with pytest.raises(ConfigError, match=r"(?s)\.vekna\.toml: \[cabinet\].*gates"):
            read_project(IDENTIFY_NEEDS)

    @staticmethod
    def test_a_file_that_will_not_parse_dies_at_the_boundary(here: Path) -> None:
        (here / ".vekna.toml").write_text('[cabinet]\ngate = "unclosed\n')

        with pytest.raises(RitualDefinitionError, match=r"\.vekna\.toml: "):
            read_project(HEAL_NEEDS)
