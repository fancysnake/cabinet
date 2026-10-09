"""What is said to git, and what is made of the answer."""

import pytest
from pydantic import BaseModel
from vekna.lexicon import Done, step
from vekna.trial import Trial

from cabinet.links.scm.git import GitScm
from cabinet.links.tasks.mise import MiseTasks
from cabinet.pacts.project import Project
from cabinet.pacts.scm import ScmError
from cabinet.pacts.tasks import Ran

_SCM = GitScm(Project())
_UNSIGNED = GitScm(Project(sign_commits=False))
_GITLAB = GitScm(Project(forge="gitlab", remote="lab"))

_STATUS = "git status --porcelain"
_HERE = "git rev-parse --abbrev-ref HEAD"
_GPG_TTY = 'GPG_TTY="${GPG_TTY:-$(tty </dev/tty 2>/dev/null)}"'
_COMMIT = f"git add -A && (git diff --cached --quiet || {_GPG_TTY} git commit -m fix)"
_RELEASE = (
    "if git rev-parse -q --verify MERGE_HEAD >/dev/null; then git merge --abort; fi; "
    f'if [ -n "$({_STATUS})" ]; then git stash push -u -m '
    "'a pr sweep left feature unfinished' >/dev/null && echo stashed; fi"
)


class _Ask(BaseModel):
    branch: str = "feature"


# One class per step: vekna routes by payload class, so no two steps share one.
class _AskPreflight(_Ask):
    pass


class _AskPreflightGitlab(_Ask):
    pass


class _AskStatus(_Ask):
    pass


class _AskHere(_Ask):
    pass


class _AskCheckout(_Ask):
    pass


class _AskSyncBase(_Ask):
    pass


class _AskCatchUp(_Ask):
    pass


class _AskContains(_Ask):
    pass


class _AskMerge(_Ask):
    pass


class _AskUnmerged(_Ask):
    pass


class _AskContinueMerge(_Ask):
    pass


class _AskCommit(_Ask):
    pass


class _AskCommitUnsigned(_Ask):
    pass


class _AskPush(_Ask):
    pass


class _AskRelease(_Ask):
    pass


class _AskAhead(_Ask):
    pass


class _AskTask(_Ask):
    pass


class _Text(BaseModel):
    text: str


class _Flag(BaseModel):
    flag: bool


class _Count(BaseModel):
    count: int | None


class _Files(BaseModel):
    files: list[str]


@step
async def preflight(_: _AskPreflight) -> Done[None]:
    await _SCM.preflight()
    return Done(None)


@step
async def preflight_gitlab(_: _AskPreflightGitlab) -> Done[None]:
    await _GITLAB.preflight()
    return Done(None)


@step
async def status(_: _AskStatus) -> Done[_Text]:
    return Done(_Text(text=await _SCM.status()))


@step
async def here(_: _AskHere) -> Done[_Text]:
    return Done(_Text(text=await _SCM.here()))


@step
async def checkout(ask: _AskCheckout) -> Done[None]:
    await _SCM.checkout(ask.branch)
    return Done(None)


@step
async def sync_base(_: _AskSyncBase) -> Done[None]:
    await _SCM.sync_base("main")
    return Done(None)


@step
async def catch_up(ask: _AskCatchUp) -> Done[None]:
    await _SCM.catch_up(ask.branch)
    return Done(None)


@step
async def contains(_: _AskContains) -> Done[_Flag]:
    return Done(_Flag(flag=await _SCM.contains("main")))


@step
async def merge(_: _AskMerge) -> Done[Ran]:
    return Done(await _SCM.merge("main"))


@step
async def unmerged(_: _AskUnmerged) -> Done[_Files]:
    return Done(_Files(files=await _SCM.unmerged()))


@step
async def continue_merge(_: _AskContinueMerge) -> Done[None]:
    await _SCM.continue_merge()
    return Done(None)


@step
async def commit(_: _AskCommit) -> Done[None]:
    await _SCM.commit("fix")
    return Done(None)


@step
async def commit_unsigned(_: _AskCommitUnsigned) -> Done[None]:
    await _UNSIGNED.commit("fix")
    return Done(None)


@step
async def push(ask: _AskPush) -> Done[None]:
    await _SCM.push(ask.branch)
    return Done(None)


@step
async def release(ask: _AskRelease) -> Done[_Text]:
    return Done(_Text(text=await _SCM.release(ask.branch)))


@step
async def ahead(ask: _AskAhead) -> Done[_Count]:
    return Done(_Count(count=await _SCM.ahead(ask.branch)))


@step
async def task(_: _AskTask) -> Done[Ran]:
    return Done(await MiseTasks().run("mise run pr-fix"))


class TestPreflight:
    @staticmethod
    def test_an_https_remote_with_a_helper_passes(trial: Trial) -> None:
        trial.shell.replies(
            when="git remote get-url origin", stdout="https://github.com/o/r.git\n"
        )
        trial.shell.replies(when="git config --get-urlmatch*", stdout="!gh auth\n")

        trial.walk(preflight, _AskPreflight())

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
            trial.walk(preflight, _AskPreflight())

    @staticmethod
    def test_a_missing_helper_names_the_forge_fix(trial: Trial) -> None:
        trial.shell.replies(
            when="git remote get-url lab", stdout="https://gitlab.example/o/r.git\n"
        )
        trial.shell.replies(when="git config --get-urlmatch*", exit_code=1)

        with pytest.raises(ScmError, match=r"no credential helper.*glab auth"):
            trial.walk(preflight_gitlab, _AskPreflightGitlab())

    @staticmethod
    def test_a_remote_that_is_not_there(trial: Trial) -> None:
        trial.shell.replies(when="git remote get-url origin", exit_code=2)

        with pytest.raises(ScmError, match="no remote named origin: exit code 2"):
            trial.walk(preflight, _AskPreflight())


class TestReading:
    @staticmethod
    def test_status_is_the_porcelain_text(trial: Trial) -> None:
        trial.shell.replies(when=_STATUS, stdout=" M a.py\n")

        assert trial.walk(status, _AskStatus()) == Done(_Text(text="M a.py"))

    @staticmethod
    def test_a_status_that_fails_raises(trial: Trial) -> None:
        trial.shell.replies(when=_STATUS, exit_code=128, stderr="not a repo")

        with pytest.raises(ScmError, match="git status failed: not a repo"):
            trial.walk(status, _AskStatus())

    @staticmethod
    def test_here_is_the_branch(trial: Trial) -> None:
        trial.shell.replies(when=_HERE, stdout="feature\n")

        assert trial.walk(here, _AskHere()) == Done(_Text(text="feature"))

    @staticmethod
    def test_contains_is_the_exit_code(trial: Trial) -> None:
        trial.shell.replies(when="git merge-base --is-ancestor main HEAD", exit_code=1)

        assert trial.walk(contains, _AskContains()) == Done(_Flag(flag=False))

    @staticmethod
    def test_unmerged_is_a_list_of_paths(trial: Trial) -> None:
        trial.shell.replies(
            when="git diff --name-only --diff-filter=U", stdout="a.py\nb.py\n"
        )

        assert trial.walk(unmerged, _AskUnmerged()) == Done(
            _Files(files=["a.py", "b.py"])
        )

    # `--name-only` leaves a space in a path unquoted, so splitting on
    # whitespace would hand the resolver two files that do not exist.
    @staticmethod
    def test_a_path_with_a_space_is_one_path(trial: Trial) -> None:
        trial.shell.replies(
            when="git diff --name-only --diff-filter=U",
            stdout="docs/release notes.md\na.py\n",
        )

        assert trial.walk(unmerged, _AskUnmerged()) == Done(
            _Files(files=["docs/release notes.md", "a.py"])
        )

    @staticmethod
    def test_merge_hands_back_what_git_said(trial: Trial) -> None:
        trial.shell.replies(
            when="git merge --no-edit main", exit_code=1, stdout="CONFLICT"
        )

        assert trial.walk(merge, _AskMerge()) == Done(
            Ran(stdout="CONFLICT", stderr="", exit_code=1)
        )


class TestMoving:
    @staticmethod
    def test_checkout(trial: Trial) -> None:
        trial.shell.replies(when="git checkout feature")

        trial.walk(checkout, _AskCheckout())

        assert trial.shell.commands == ["git checkout feature"]

    @staticmethod
    def test_a_checkout_that_will_not_go_through(trial: Trial) -> None:
        trial.shell.replies(when="git checkout feature", exit_code=1, stderr="busy")

        with pytest.raises(ScmError, match="could not take feature: busy"):
            trial.walk(checkout, _AskCheckout())

    @staticmethod
    def test_sync_base_fetches_stands_and_pulls(trial: Trial) -> None:
        trial.shell.replies(when="git fetch*")

        trial.walk(sync_base, _AskSyncBase())

        assert trial.shell.commands == [
            (
                "git fetch --prune origin && git checkout main"
                " && git pull --ff-only origin main"
            )
        ]

    @staticmethod
    def test_catch_up_is_a_fast_forward_only(trial: Trial) -> None:
        trial.shell.replies(when="git merge --ff-only*")

        trial.walk(catch_up, _AskCatchUp())

        assert trial.shell.commands == ["git merge --ff-only origin/feature"]

    @staticmethod
    def test_continue_merge_only_where_one_is_open(trial: Trial) -> None:
        trial.shell.replies(when="if git rev-parse*")

        trial.walk(continue_merge, _AskContinueMerge())

        assert trial.shell.commands == [
            (
                "if git rev-parse -q --verify MERGE_HEAD >/dev/null; then "
                "git add -A && git -c core.editor=true merge --continue; fi"
            )
        ]

    @staticmethod
    def test_push_goes_to_the_named_remote(trial: Trial) -> None:
        trial.shell.replies(when="git push*")

        trial.walk(push, _AskPush())

        assert trial.shell.commands == ["git push origin feature"]

    @staticmethod
    def test_a_push_that_fails(trial: Trial) -> None:
        trial.shell.replies(when="git push*", exit_code=1, stderr="rejected")

        with pytest.raises(ScmError, match="could not push feature: rejected"):
            trial.walk(push, _AskPush())


class TestCommit:
    @staticmethod
    def test_stages_everything_and_names_the_tty(trial: Trial) -> None:
        trial.shell.replies(when="git add -A*")

        trial.walk(commit, _AskCommit())

        assert trial.shell.commands == [_COMMIT]

    @staticmethod
    def test_unsigned_where_the_project_says_so(trial: Trial) -> None:
        trial.shell.replies(when="git add -A*")

        trial.walk(commit_unsigned, _AskCommitUnsigned())

        assert trial.shell.commands == [
            _COMMIT.replace(" git commit", " git -c commit.gpgsign=false commit")
        ]

    @staticmethod
    def test_a_commit_that_fails(trial: Trial) -> None:
        trial.shell.replies(when="git add -A*", exit_code=1, stderr="gpg failed")

        with pytest.raises(ScmError, match="could not commit: gpg failed"):
            trial.walk(commit, _AskCommit())


class TestRelease:
    @staticmethod
    def test_says_whether_a_stash_was_made(trial: Trial) -> None:
        trial.shell.replies(when="if git rev-parse*", stdout="stashed\n")

        assert trial.walk(release, _AskRelease()) == Done(
            _Text(text="a pr sweep left feature unfinished")
        )
        assert trial.shell.commands == [_RELEASE]

    @staticmethod
    def test_a_clean_tree_stashes_nothing(trial: Trial) -> None:
        trial.shell.replies(when="if git rev-parse*")

        assert trial.walk(release, _AskRelease()) == Done(_Text(text=""))


class TestAhead:
    @staticmethod
    def test_counts_against_the_remote(trial: Trial) -> None:
        trial.shell.replies(when="test feature*", stdout="2\n")

        assert trial.walk(ahead, _AskAhead()) == Done(_Count(count=2))
        assert trial.shell.commands == [
            f'test feature = "$({_HERE})" && git rev-list --count origin/feature..HEAD'
        ]

    @staticmethod
    def test_none_where_git_could_not_say(trial: Trial) -> None:
        trial.shell.replies(when="test feature*", exit_code=1)

        assert trial.walk(ahead, _AskAhead()) == Done(_Count(count=None))

    @staticmethod
    def test_none_where_the_answer_is_not_a_number(trial: Trial) -> None:
        trial.shell.replies(when="test feature*", stdout="fatal\n")

        assert trial.walk(ahead, _AskAhead()) == Done(_Count(count=None))


class TestMise:
    @staticmethod
    def test_a_task_runs_captured_under_ci(trial: Trial) -> None:
        trial.shell.replies(
            when="CI=1 mise run pr-fix", exit_code=1, stdout="1 failed", stderr="x"
        )

        assert trial.walk(task, _AskTask()) == Done(
            Ran(stdout="1 failed", stderr="x", exit_code=1)
        )
        assert trial.shell.calls[0].command == "CI=1 mise run pr-fix"
