"""The `[cabinet]` section, found the way vekna finds its own."""

import os
from pathlib import Path

import pytest

from cabinet.links.config.vekna_toml import read_project
from cabinet.pacts.project import ConfigError, Project

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

    # A syntax error is a configuration failure like any other: the cast is
    # owed the file's name, not a raw TOMLDecodeError out of startup.
    @staticmethod
    def test_a_file_that_will_not_parse_dies_at_the_boundary(tmp_path: Path) -> None:
        (tmp_path / ".vekna.toml").write_text('[cabinet]\ngate = "unclosed\n')

        with pytest.raises(ConfigError, match=r"\.vekna\.toml: "):
            read_project(tmp_path)

    # Root opens a file it has no permission bits for, so the error this
    # waits on never comes and the assertion is about the runner, not the
    # boundary.
    @staticmethod
    @pytest.mark.skipif(os.geteuid() == 0, reason="root ignores the mode bits")
    def test_a_file_that_will_not_open_dies_at_the_boundary(tmp_path: Path) -> None:
        named = tmp_path / ".vekna.toml"
        named.write_text(_SECTION)
        named.chmod(0o000)

        with pytest.raises(ConfigError, match=r"\.vekna\.toml could not be read"):
            read_project(tmp_path)

    @staticmethod
    def test_no_file_anywhere_up(tmp_path: Path) -> None:
        with pytest.raises(ConfigError, match=r"no \.vekna\.toml found"):
            read_project(tmp_path)
