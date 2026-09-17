"""The `[cabinet]` section, found the way vekna finds its own."""

from typing import TYPE_CHECKING

import pytest

from cabinet.links.config.vekna_toml import read_project
from cabinet.pacts.project import ConfigError, Project

if TYPE_CHECKING:
    from pathlib import Path

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
may_run = ["mise run test:unit"]
"""


class TestReadProject:
    @staticmethod
    def test_the_section_is_read_and_the_rest_is_ignored(tmp_path: Path) -> None:
        (tmp_path / ".vekna.toml").write_text(_SECTION)

        project = read_project(tmp_path)

        assert project.forge == "gitlab"
        assert project.gate == "mise run check"
        assert project.sign_commits is False
        assert project.labels.wait == "hold"
        assert project.labels.reviewed == "pr::thermo"
        assert project.agent.may_run == ["mise run test:unit"]

    @staticmethod
    def test_found_by_walking_up(tmp_path: Path) -> None:
        (tmp_path / ".vekna.toml").write_text(_SECTION)
        nested = tmp_path / "src" / "pkg"
        nested.mkdir(parents=True)

        assert read_project(nested).forge == "gitlab"

    @staticmethod
    def test_a_file_without_the_section_means_the_defaults(tmp_path: Path) -> None:
        (tmp_path / ".vekna.toml").write_text(
            '[rituals]\nmodules = ["cabinet.rituals"]\n'
        )

        assert read_project(tmp_path) == Project()

    @staticmethod
    def test_a_typo_dies_at_the_boundary(tmp_path: Path) -> None:
        (tmp_path / ".vekna.toml").write_text('[cabinet]\ngates = "mise run x"\n')

        with pytest.raises(ConfigError, match=r"(?s)\.vekna\.toml: \[cabinet\].*gates"):
            read_project(tmp_path)

    @staticmethod
    def test_no_file_anywhere_up(tmp_path: Path) -> None:
        with pytest.raises(ConfigError, match=r"no \.vekna\.toml found"):
            read_project(tmp_path)
