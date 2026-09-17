"""What is said to gh, and what is made of the answer."""

import json
import shlex
from typing import TYPE_CHECKING

import pytest
from pydantic import BaseModel
from vekna.lexicon import Transition, done, step

from cabinet.links.forge.github import GithubForge
from cabinet.pacts.forge import ForgeError
from cabinet.pacts.pulls import Board, Check, PullRequest
from cabinet.pacts.threads import Comment, Finding, Thread

if TYPE_CHECKING:
    from vekna.trial import Trial

_FORGE = GithubForge()

_LIST = (
    "gh pr list --author @me --state open "
    "--json number,title,headRefName,baseRefName,url,updatedAt,labels"
)
_BOARD = "gh api 'repos/{owner}/{repo}/commits/feature/check-runs?per_page=100'"
_THREAD = Thread(
    id="PRRT_1",
    resolved=False,
    path="src/thing.py",
    line=12,
    comments=[Comment(id="101", author="reviewer", body="guard this")],
)


def _row(number: int, **extra: object) -> dict[str, object]:
    return {
        "number": number,
        "title": f"pr {number}",
        "headRefName": f"feature-{number}",
        "baseRefName": "main",
        "url": f"https://github.com/o/r/pull/{number}",
        "updatedAt": "2026-08-01T22:00:00Z",
        "labels": [],
        **extra,
    }


class _Ask(BaseModel):
    number: int = 7


class _Pulls(BaseModel):
    pulls: list[PullRequest]


class _Labels(BaseModel):
    labels: list[str]


class _Threads(BaseModel):
    threads: list[Thread]


class _Made(BaseModel):
    url: str


@step
async def pulls(_: _Ask) -> Transition:
    return done(_Pulls(pulls=await _FORGE.pulls()))


@step
async def labels(ask: _Ask) -> Transition:
    return done(_Labels(labels=await _FORGE.labels(ask.number)))


@step
async def label(ask: _Ask) -> Transition:
    await _FORGE.label(ask.number, add=["v:refresh:started"], remove=["v:refresh:done"])
    return done()


@step
async def threads(ask: _Ask) -> Transition:
    return done(_Threads(threads=await _FORGE.threads(ask.number)))


@step
async def reply(ask: _Ask) -> Transition:
    await _FORGE.reply(ask.number, _THREAD, "done")
    return done()


@step
async def resolve(ask: _Ask) -> Transition:
    await _FORGE.resolve(ask.number, _THREAD)
    return done()


@step
async def board(_: _Ask) -> Transition:
    return done(await _FORGE.board("feature"))


@step
async def anchored(ask: _Ask) -> Transition:
    await _FORGE.comment(ask.number, Finding(path="src/thing.py", line=12, body="hm"))
    return done()


@step
async def general(ask: _Ask) -> Transition:
    await _FORGE.comment(ask.number, Finding(path="", body="hm"))
    return done()


@step
async def issue(_: _Ask) -> Transition:
    return done(_Made(url=await _FORGE.issue("a title", "a body")))


class TestPulls:
    @staticmethod
    def test_the_listing_is_read_into_pull_requests(trial: Trial) -> None:
        trial.shell.replies(
            when=_LIST, stdout=json.dumps([_row(7, labels=[{"name": "pr::wait"}])])
        )

        transition = trial.walk(pulls, _Ask())

        assert transition == done(
            _Pulls(
                pulls=[
                    PullRequest(
                        number=7,
                        title="pr 7",
                        url="https://github.com/o/r/pull/7",
                        branch="feature-7",
                        base="main",
                        updated_at="2026-08-01T22:00:00Z",
                        labels=["pr::wait"],
                    )
                ]
            )
        )
        assert trial.shell.commands == [_LIST]

    @staticmethod
    def test_a_gh_that_will_not_answer(trial: Trial) -> None:
        trial.shell.replies(when=_LIST, exit_code=1, stderr="not logged in")

        with pytest.raises(ForgeError, match=r"could not list.*not logged in"):
            trial.walk(pulls, _Ask())

    @staticmethod
    def test_a_listing_that_will_not_parse(trial: Trial) -> None:
        trial.shell.replies(when=_LIST, stdout="[{}]")

        with pytest.raises(ForgeError, match="unreadable"):
            trial.walk(pulls, _Ask())


class TestLabels:
    @staticmethod
    def test_names_only(trial: Trial) -> None:
        trial.shell.replies(
            when="gh pr view 7 --json labels",
            stdout='{"labels": [{"name": "bug"}, {"name": "pr::thermo"}]}',
        )

        assert trial.walk(labels, _Ask()) == done(_Labels(labels=["bug", "pr::thermo"]))

    @staticmethod
    def test_labels_that_will_not_parse(trial: Trial) -> None:
        trial.shell.replies(when="gh pr view 7 --json labels", stdout='{"labels": 1}')

        with pytest.raises(ForgeError, match="labels this could not read"):
            trial.walk(labels, _Ask())

    @staticmethod
    def test_both_halves_go_in_one_call(trial: Trial) -> None:
        trial.shell.replies(when="gh pr edit 7*")

        trial.walk(label, _Ask())

        assert trial.shell.commands == [
            "gh pr edit 7 --add-label v:refresh:started --remove-label v:refresh:done"
        ]

    @staticmethod
    def test_nothing_to_change_is_no_call(trial: Trial) -> None:
        @step
        async def nothing(ask: _Ask) -> Transition:
            await _FORGE.label(ask.number)
            return done()

        trial.walk(nothing, _Ask())

        assert not trial.shell.commands

    @staticmethod
    def test_a_label_gh_refuses(trial: Trial) -> None:
        trial.shell.replies(when="gh pr edit 7*", exit_code=1, stderr="no such label")

        with pytest.raises(ForgeError, match="could not label #7"):
            trial.walk(label, _Ask())


class TestThreads:
    @staticmethod
    def test_graphql_nodes_become_threads(trial: Trial) -> None:
        answer = {
            "data": {
                "repository": {
                    "pullRequest": {
                        "reviewThreads": {
                            "nodes": [
                                {
                                    "id": "PRRT_1",
                                    "isResolved": False,
                                    "path": "src/thing.py",
                                    "line": 12,
                                    "comments": {
                                        "nodes": [
                                            {
                                                "databaseId": 101,
                                                "author": {"login": "reviewer"},
                                                "body": "guard this",
                                            }
                                        ]
                                    },
                                },
                                {
                                    "id": "PRRT_2",
                                    "isResolved": True,
                                    "path": None,
                                    "line": None,
                                    "comments": {"nodes": []},
                                },
                            ]
                        }
                    }
                }
            }
        }
        trial.shell.replies(when="slug=*gh api graphql*", stdout=json.dumps(answer))

        transition = trial.walk(threads, _Ask())

        assert transition == done(
            _Threads(threads=[_THREAD, Thread(id="PRRT_2", resolved=True)])
        )
        assert trial.shell.commands[0].endswith(' -f repo="${slug#*/}" -F number=7')

    @staticmethod
    def test_an_answer_that_will_not_parse(trial: Trial) -> None:
        nodes = {"reviewThreads": {"nodes": [{"id": "PRRT_1"}]}}
        answer = {"data": {"repository": {"pullRequest": nodes}}}
        trial.shell.replies(when="slug=*gh api graphql*", stdout=json.dumps(answer))

        with pytest.raises(ForgeError, match="threads this could not read"):
            trial.walk(threads, _Ask())

    @staticmethod
    def test_a_reply_goes_under_the_first_comment(trial: Trial) -> None:
        trial.shell.replies(when="gh api repos/*")

        trial.walk(reply, _Ask())

        assert trial.shell.commands == [
            "gh api repos/{owner}/{repo}/pulls/7/comments/101/replies -f body=done"
        ]

    @staticmethod
    def test_a_thread_without_comments_cannot_be_answered(trial: Trial) -> None:
        bare = Thread(id="PRRT_9", resolved=False)

        @step
        async def replying(ask: _Ask) -> Transition:
            await _FORGE.reply(ask.number, bare, "done")
            return done()

        with pytest.raises(ForgeError, match="no comment to reply under"):
            trial.walk(replying, _Ask())

    @staticmethod
    def test_resolving_takes_the_node_id(trial: Trial) -> None:
        trial.shell.replies(when="slug=*gh api graphql*")

        trial.walk(resolve, _Ask())

        assert trial.shell.commands[0].endswith(' -f repo="${slug#*/}" -f id=PRRT_1')


class TestBoard:
    @staticmethod
    def test_check_runs_become_checks(trial: Trial) -> None:
        answer = {
            "total_count": 3,
            "check_runs": [
                {"name": "test", "conclusion": "success"},
                {"name": "checks", "conclusion": "failure", "output": {"title": None}},
                {
                    "name": "codecov/patch",
                    "conclusion": None,
                    "output": {"title": "96.84% of diff hit"},
                },
            ],
        }
        trial.shell.replies(when=_BOARD, stdout=json.dumps(answer))

        assert trial.walk(board, _Ask()) == done(
            Board(
                checks=[
                    Check(name="test", passed=True),
                    Check(name="checks", passed=False),
                    Check(name="codecov/patch", title="96.84% of diff hit"),
                ]
            )
        )

    @staticmethod
    def test_a_short_page_says_so(trial: Trial) -> None:
        trial.shell.replies(
            when=_BOARD, stdout='{"total_count": 2, "check_runs": [{"name": "test"}]}'
        )

        assert trial.walk(board, _Ask()) == done(
            Board(checks=[Check(name="test")], truncated=True)
        )

    @staticmethod
    def test_a_board_that_will_not_parse(trial: Trial) -> None:
        trial.shell.replies(when=_BOARD, stdout='{"check_runs": 1}')

        with pytest.raises(ForgeError, match="board this could not read"):
            trial.walk(board, _Ask())

    @staticmethod
    def test_a_board_gh_would_not_give(trial: Trial) -> None:
        trial.shell.replies(when=_BOARD, exit_code=1, stderr="502")

        with pytest.raises(ForgeError, match=r"check board.*502"):
            trial.walk(board, _Ask())


class TestComment:
    @staticmethod
    def test_an_anchored_item_is_posted_on_its_line(trial: Trial) -> None:
        trial.shell.replies(when="gh pr view 7 --json headRefOid*", stdout="abc123\n")
        trial.shell.replies(when="gh api repos/*")

        trial.walk(anchored, _Ask())

        assert trial.shell.commands == [
            "gh pr view 7 --json headRefOid -q .headRefOid",
            (
                "gh api repos/{owner}/{repo}/pulls/7/comments -f commit_id=abc123"
                " -f path=src/thing.py -F line=12 -f side=RIGHT -f body=hm"
            ),
        ]

    @staticmethod
    def test_a_refused_anchor_falls_back_to_a_plain_comment(trial: Trial) -> None:
        trial.shell.replies(when="gh pr view 7 --json headRefOid*", stdout="abc123\n")
        trial.shell.replies(when="gh api repos/*", exit_code=1, stderr="422")
        trial.shell.replies(when="gh pr comment 7*")

        trial.walk(anchored, _Ask())

        assert trial.shell.commands[-1] == "gh pr comment 7 --body hm"

    @staticmethod
    def test_a_general_item_is_a_plain_comment(trial: Trial) -> None:
        trial.shell.replies(when="gh pr comment 7*")

        trial.walk(general, _Ask())

        assert trial.shell.commands == ["gh pr comment 7 --body hm"]

    @staticmethod
    def test_a_comment_gh_refuses(trial: Trial) -> None:
        trial.shell.replies(when="gh pr comment 7*", exit_code=1, stderr="403")

        with pytest.raises(ForgeError, match="could not comment on #7"):
            trial.walk(general, _Ask())


class TestIssue:
    @staticmethod
    def test_the_url_comes_back(trial: Trial) -> None:
        trial.shell.replies(
            when="gh issue create*", stdout="https://github.com/o/r/issues/9\n"
        )

        assert trial.walk(issue, _Ask()) == done(
            _Made(url="https://github.com/o/r/issues/9")
        )
        assert trial.shell.commands == [
            (
                f"gh issue create --title {shlex.quote('a title')}"
                f" --body {shlex.quote('a body')}"
            )
        ]
