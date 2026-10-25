"""What is said to git, and what is made of the answer."""

import os
import subprocess
from pathlib import Path

import pytest
from vekna.trial import Trial

from cabinet.links.scm.git import GitScm
from cabinet.links.tasks.mise import MiseTasks
from cabinet.pacts.project import Project
from cabinet.pacts.scm import ScmError
from cabinet.pacts.tasks import Ran
from tests.conftest import drive

_SCM = GitScm(Project())
_UNSIGNED = GitScm(Project(sign_commits=False))
_GITLAB = GitScm(Project(forge="gitlab", remote="lab"))
_ELSEWHERE = {"GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE"}
_ISOLATED = {k: v for k, v in os.environ.items() if k not in _ELSEWHERE} | {
    "GIT_CONFIG_GLOBAL": "/dev/null",
    "GIT_CONFIG_NOSYSTEM": "1",
}

_STATUS = "git status --porcelain"
_HERE = "git rev-parse --abbrev-ref HEAD"
_AHEAD = 2
_FETCH = "git fetch origin main feature"
_MERGE_TREE = "git merge-tree --write-tree origin/main origin/feature > /dev/null"
_GPG_TTY = 'GPG_TTY="${GPG_TTY:-$(tty </dev/tty 2>/dev/null)}"'
_COMMIT = (
    "git add -A && (git diff --cached --quiet || ("
    f"{_GPG_TTY} git commit -m fix && echo committed))"
)
_RELEASE = (
    "if git rev-parse -q --verify MERGE_HEAD >/dev/null; then git merge --abort; fi; "
    f'if [ -n "$({_STATUS})" ]; then git stash push -u -m '
    "'a pr sweep left feature unfinished' >/dev/null && echo stashed; fi"
)


class TestPreflight:
    @staticmethod
    def test_an_https_remote_with_a_helper_passes(trial: Trial) -> None:
        trial.shell.replies(
            when="git remote get-url origin", stdout="https://github.com/o/r.git\n"
        )
        trial.shell.replies(when="git config --get-urlmatch*", stdout="!gh auth\n")

        drive(trial, _SCM.preflight)

        assert trial.shell.commands == [
            "git remote get-url origin",
            "git config --get-urlmatch credential.helper https://github.com/o/r.git",
        ]

    @staticmethod
    def test_an_ssh_remote_is_refused_before_any_fetch(trial: Trial) -> None:
        trial.shell.replies(
            when="git remote get-url origin", stdout="git@github.com:o/r.git\n"
        )

        with pytest.raises(ScmError, match=r"not https.*gh auth setup-git"):
            drive(trial, _SCM.preflight)

    @staticmethod
    def test_a_missing_helper_names_the_forge_fix(trial: Trial) -> None:
        trial.shell.replies(
            when="git remote get-url lab", stdout="https://gitlab.example/o/r.git\n"
        )
        trial.shell.replies(when="git config --get-urlmatch*", exit_code=1)

        with pytest.raises(ScmError, match=r"no credential helper.*glab auth"):
            drive(trial, _GITLAB.preflight)

    @staticmethod
    def test_a_remote_that_is_not_there(trial: Trial) -> None:
        trial.shell.replies(when="git remote get-url origin", exit_code=2)

        with pytest.raises(ScmError, match="no remote named origin: exit code 2"):
            drive(trial, _SCM.preflight)


class TestReading:
    @staticmethod
    def test_status_is_the_porcelain_text(trial: Trial) -> None:
        trial.shell.replies(when=_STATUS, stdout=" M a.py\n")

        assert drive(trial, _SCM.status) == "M a.py"

    @staticmethod
    def test_a_status_that_fails_raises(trial: Trial) -> None:
        trial.shell.replies(when=_STATUS, exit_code=128, stderr="not a repo")

        with pytest.raises(ScmError, match="git status failed: not a repo"):
            drive(trial, _SCM.status)

    @staticmethod
    def test_here_is_the_branch(trial: Trial) -> None:
        trial.shell.replies(when=_HERE, stdout="feature\n")

        assert drive(trial, _SCM.here) == "feature"

    @staticmethod
    def test_contains_is_the_exit_code(trial: Trial) -> None:
        trial.shell.replies(when="git merge-base --is-ancestor main HEAD", exit_code=1)

        assert not drive(trial, lambda: _SCM.contains("main"))

    @staticmethod
    def test_unmerged_is_a_list_of_paths(trial: Trial) -> None:
        trial.shell.replies(
            when="git diff --name-only --diff-filter=U", stdout="a.py\nb.py\n"
        )

        assert drive(trial, _SCM.unmerged) == ["a.py", "b.py"]

    # `--name-only` leaves a space in a path unquoted, so splitting on
    # whitespace would hand the resolver two files that do not exist.
    @staticmethod
    def test_a_path_with_a_space_is_one_path(trial: Trial) -> None:
        trial.shell.replies(
            when="git diff --name-only --diff-filter=U",
            stdout="docs/release notes.md\na.py\n",
        )

        assert drive(trial, _SCM.unmerged) == ["docs/release notes.md", "a.py"]

    @staticmethod
    def test_merge_hands_back_what_git_said(trial: Trial) -> None:
        trial.shell.replies(
            when="git merge --no-edit main", exit_code=1, stdout="CONFLICT"
        )

        assert drive(trial, lambda: _SCM.merge("main")) == Ran(
            stdout="CONFLICT", stderr="", exit_code=1
        )


class TestMoving:
    @staticmethod
    def test_checkout(trial: Trial) -> None:
        trial.shell.replies(when="git checkout feature")

        drive(trial, lambda: _SCM.checkout("feature"))

        assert trial.shell.commands == ["git checkout feature"]

    @staticmethod
    def test_a_checkout_that_will_not_go_through(trial: Trial) -> None:
        trial.shell.replies(when="git checkout feature", exit_code=1, stderr="busy")

        with pytest.raises(ScmError, match="could not take feature: busy"):
            drive(trial, lambda: _SCM.checkout("feature"))

    @staticmethod
    def test_sync_base_fetches_stands_and_pulls(trial: Trial) -> None:
        trial.shell.replies(when="git fetch*")

        drive(trial, lambda: _SCM.sync_base("main"))

        assert trial.shell.commands == [
            (
                "git fetch --prune origin && git checkout main"
                " && git pull --ff-only origin main"
            )
        ]

    @staticmethod
    def test_catch_up_is_a_fast_forward_only(trial: Trial) -> None:
        trial.shell.replies(when="git merge --ff-only*")

        drive(trial, lambda: _SCM.catch_up("feature"))

        assert trial.shell.commands == ["git merge --ff-only origin/feature"]

    @staticmethod
    def test_continue_merge_only_where_one_is_open(trial: Trial) -> None:
        trial.shell.replies(when="if git rev-parse*")

        drive(trial, _SCM.continue_merge)

        assert trial.shell.commands == [
            (
                "if git rev-parse -q --verify MERGE_HEAD >/dev/null; then "
                "git add -A && git -c core.editor=true merge --continue; fi"
            )
        ]

    @staticmethod
    def test_push_goes_to_the_named_remote(trial: Trial) -> None:
        trial.shell.replies(when="git push*")

        drive(trial, lambda: _SCM.push("feature"))

        assert trial.shell.commands == ["git push origin feature"]

    @staticmethod
    def test_a_push_that_fails(trial: Trial) -> None:
        trial.shell.replies(when="git push*", exit_code=1, stderr="rejected")

        with pytest.raises(ScmError, match="could not push feature: rejected"):
            drive(trial, lambda: _SCM.push("feature"))


class TestConflicts:
    @staticmethod
    @pytest.mark.parametrize(("exit_code", "conflicts"), [(0, False), (1, True)])
    def test_merged_in_memory_against_the_remote(
        trial: Trial, exit_code: int, *, conflicts: bool
    ) -> None:
        trial.shell.replies(when=_FETCH)
        trial.shell.replies(when=_MERGE_TREE, exit_code=exit_code)

        assert drive(trial, lambda: _SCM.conflicts("main", "feature")) is conflicts
        assert trial.shell.commands == [_FETCH, _MERGE_TREE]

    @staticmethod
    def test_a_fetch_that_fails(trial: Trial) -> None:
        trial.shell.replies(when=_FETCH, exit_code=128, stderr="gone")

        with pytest.raises(ScmError, match="could not fetch main and feature: gone"):
            drive(trial, lambda: _SCM.conflicts("main", "feature"))

    @staticmethod
    def test_a_merge_git_could_not_try(trial: Trial) -> None:
        trial.shell.replies(when=_FETCH)
        trial.shell.replies(when=_MERGE_TREE, exit_code=128, stderr="bad ref")

        with pytest.raises(ScmError, match="could not try the merge: bad ref"):
            drive(trial, lambda: _SCM.conflicts("main", "feature"))


class TestCommit:
    @staticmethod
    def test_stages_everything_and_names_the_tty(trial: Trial) -> None:
        trial.shell.replies(
            when="git add -A*", stdout="[feature 1a2b] fix\ncommitted\n"
        )

        assert drive(trial, lambda: _SCM.commit("fix"))
        assert trial.shell.commands == [_COMMIT]

    @staticmethod
    def test_nothing_staged_is_nothing_committed(trial: Trial) -> None:
        trial.shell.replies(when="git add -A*")

        assert not drive(trial, lambda: _SCM.commit("fix"))

    @staticmethod
    def test_unsigned_where_the_project_says_so(trial: Trial) -> None:
        trial.shell.replies(when="git add -A*")

        drive(trial, lambda: _UNSIGNED.commit("fix"))

        assert trial.shell.commands == [
            _COMMIT.replace(" git commit", " git -c commit.gpgsign=false commit")
        ]

    @staticmethod
    def test_a_commit_that_fails(trial: Trial) -> None:
        trial.shell.replies(when="git add -A*", exit_code=1, stderr="gpg failed")

        with pytest.raises(ScmError, match="could not commit: gpg failed"):
            drive(trial, lambda: _SCM.commit("fix"))


# The scripted shell answers whatever it is told, so what bash makes of the
# operators in the commit command only shows when bash runs it.
class TestCommitInBash:
    @staticmethod
    @pytest.fixture
    def repo(tmp_path: Path) -> Path:
        for argv in (
            ["git", "init", "-q"],
            ["git", "config", "user.name", "cabinet"],
            ["git", "config", "user.email", "cabinet@example.com"],
            ["git", "commit", "-q", "--allow-empty", "-m", "root"],
        ):
            subprocess.run(argv, cwd=tmp_path, env=_ISOLATED, check=True)
        return tmp_path

    @staticmethod
    def test_a_change_is_committed_and_said(trial: Trial, repo: Path) -> None:
        (repo / "fixed.py").write_text("x = 1\n")

        assert _in_bash(trial, repo)[-1:] == ["committed"]
        assert _log(repo) == ["fix", "root"]

    @staticmethod
    def test_nothing_staged_says_nothing(trial: Trial, repo: Path) -> None:
        assert "committed" not in _in_bash(trial, repo)
        assert _log(repo) == ["root"]


def _in_bash(trial: Trial, repo: Path) -> list[str]:
    trial.shell.replies(when="git add -A*")
    drive(trial, lambda: _UNSIGNED.commit("fix"))
    ran = subprocess.run(
        ["bash", "-c", trial.shell.commands[0]],
        cwd=repo,
        env=_ISOLATED,
        capture_output=True,
        text=True,
        check=True,
    )
    return ran.stdout.splitlines()


def _log(repo: Path) -> list[str]:
    ran = subprocess.run(
        ["git", "log", "--format=%s"],
        cwd=repo,
        env=_ISOLATED,
        capture_output=True,
        text=True,
        check=True,
    )
    return ran.stdout.splitlines()


class TestRelease:
    @staticmethod
    def test_says_whether_a_stash_was_made(trial: Trial) -> None:
        trial.shell.replies(when="if git rev-parse*", stdout="stashed\n")

        assert (
            drive(trial, lambda: _SCM.release("feature"))
            == "a pr sweep left feature unfinished"
        )
        assert trial.shell.commands == [_RELEASE]

    @staticmethod
    def test_a_clean_tree_stashes_nothing(trial: Trial) -> None:
        trial.shell.replies(when="if git rev-parse*")

        assert not drive(trial, lambda: _SCM.release("feature"))


class TestAhead:
    @staticmethod
    def test_counts_against_the_remote(trial: Trial) -> None:
        trial.shell.replies(when="test feature*", stdout=f"{_AHEAD}\n")

        assert drive(trial, lambda: _SCM.ahead("feature")) == _AHEAD
        assert trial.shell.commands == [
            f'test feature = "$({_HERE})" && git rev-list --count origin/feature..HEAD'
        ]

    @staticmethod
    def test_none_where_git_could_not_say(trial: Trial) -> None:
        trial.shell.replies(when="test feature*", exit_code=1)

        assert drive(trial, lambda: _SCM.ahead("feature")) is None

    @staticmethod
    def test_none_where_the_answer_is_not_a_number(trial: Trial) -> None:
        trial.shell.replies(when="test feature*", stdout="fatal\n")

        assert drive(trial, lambda: _SCM.ahead("feature")) is None


class TestMise:
    @staticmethod
    def test_a_task_runs_captured_under_ci(trial: Trial) -> None:
        trial.shell.replies(
            when="CI=1 mise run pr-fix", exit_code=1, stdout="1 failed", stderr="x"
        )

        assert drive(trial, lambda: MiseTasks().run("mise run pr-fix")) == Ran(
            stdout="1 failed", stderr="x", exit_code=1
        )
        assert trial.shell.calls[0].command == "CI=1 mise run pr-fix"
