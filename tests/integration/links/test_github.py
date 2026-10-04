"""What is said to gh, and what is made of the answer."""

import json
import shlex

import pytest
from pydantic import BaseModel
from vekna.lexicon import Transition, done, step
from vekna.trial import Trial

from cabinet.links.forge.github import GithubForge
from cabinet.pacts.forge import ForgeError
from cabinet.pacts.issues import Issue, Listing, Opened
from cabinet.pacts.pulls import Board, Check, PullRequest
from cabinet.pacts.threads import Comment, Finding, Posted, Thread

_FORGE = GithubForge()

_LIST = (
    "gh pr list --author @me --state open --limit 100 "
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
_LAST = {"hasNextPage": False}
_GRAPHQL = "slug=*gh api graphql*"
_REPO = ' -f repo="${slug#*/}"'


# One page of a connection, with a cursor to the next where there is one.
def _page(nodes: list[dict[str, object]], cursor: str = "") -> dict[str, object]:
    info = {"hasNextPage": True, "endCursor": cursor} if cursor else _LAST
    return {"pageInfo": info, "nodes": nodes}


def _comment(number: int) -> dict[str, object]:
    return {"databaseId": number, "author": {"login": "reviewer"}, "body": "hm"}


def _node(node_id: str, comments: dict[str, object]) -> dict[str, object]:
    return {"id": node_id, "isResolved": False, "comments": comments}


def _threads_page(page: dict[str, object]) -> str:
    return json.dumps(
        {"data": {"repository": {"pullRequest": {"reviewThreads": page}}}}
    )


def _comments_page(page: dict[str, object]) -> str:
    return json.dumps({"data": {"node": {"comments": page}}})


def _open(node_id: str, *numbers: int) -> Thread:
    comments = [Comment(id=str(one), author="reviewer", body="hm") for one in numbers]
    return Thread(id=node_id, resolved=False, comments=comments)


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
    findings = [Finding(path="src/thing.py", line=12, body="hm")]
    return done(await _FORGE.comment(ask.number, findings))


@step
async def general(ask: _Ask) -> Transition:
    return done(await _FORGE.comment(ask.number, [Finding(path="", body="hm")]))


# Two anchored items in one review, which is what the head commit is read
# once for.
@step
async def several(ask: _Ask) -> Transition:
    findings = [
        Finding(path="src/thing.py", line=12, body="one"),
        Finding(path="src/other.py", line=3, body="two"),
    ]
    return done(await _FORGE.comment(ask.number, findings))


@step
async def issue(_: _Ask) -> Transition:
    return done(await _FORGE.issue("a title", "a body"))


@step
async def label_issue(ask: _Ask) -> Transition:
    await _FORGE.label_issue(ask.number, add=["bug"], remove=["epic"])
    return done()


@step
async def attach(ask: _Ask) -> Transition:
    await _FORGE.attach(ask.number, 9)
    return done()


@step
async def blocks(ask: _Ask) -> Transition:
    await _FORGE.blocks(ask.number, 9)
    return done()


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
                            "pageInfo": _LAST,
                            "nodes": [
                                {
                                    "id": "PRRT_1",
                                    "isResolved": False,
                                    "path": "src/thing.py",
                                    "line": 12,
                                    "comments": {
                                        "pageInfo": _LAST,
                                        "nodes": [
                                            {
                                                "databaseId": 101,
                                                "author": {"login": "reviewer"},
                                                "body": "guard this",
                                            }
                                        ],
                                    },
                                },
                                {
                                    "id": "PRRT_2",
                                    "isResolved": True,
                                    "path": None,
                                    "line": None,
                                    "comments": {"pageInfo": _LAST, "nodes": []},
                                },
                            ],
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
    def test_threads_past_the_first_page_are_asked_for(trial: Trial) -> None:
        first = _page([_node("PRRT_1", _page([_comment(101)]))], cursor="c1")
        second = _page([_node("PRRT_2", _page([_comment(102)]))])
        trial.shell.replies(when=_GRAPHQL, stdout=_threads_page(first))
        trial.shell.replies(when=_GRAPHQL, stdout=_threads_page(second))

        transition = trial.walk(threads, _Ask())

        assert transition == done(
            _Threads(threads=[_open("PRRT_1", 101), _open("PRRT_2", 102)])
        )
        assert trial.shell.commands[0].endswith(f"{_REPO} -F number=7")
        assert trial.shell.commands[1].endswith(f"{_REPO} -f after=c1 -F number=7")

    @staticmethod
    def test_a_full_last_page_is_the_last(trial: Trial) -> None:
        nodes = [_node(f"PRRT_{one}", _page([])) for one in range(100)]
        trial.shell.replies(when=_GRAPHQL, stdout=_threads_page(_page(nodes)))

        transition = trial.walk(threads, _Ask())

        assert transition == done(
            _Threads(threads=[_open(f"PRRT_{one}") for one in range(100)])
        )
        assert len(trial.shell.commands) == 1

    @staticmethod
    def test_comments_past_the_first_page_are_asked_for(trial: Trial) -> None:
        held = _page([_node("PRRT_1", _page([_comment(101)], cursor="k1"))])
        rest = _page([_comment(102)], cursor="k2")
        trial.shell.replies(when=_GRAPHQL, stdout=_threads_page(held))
        trial.shell.replies(when=_GRAPHQL, stdout=_comments_page(rest))
        trial.shell.replies(when=_GRAPHQL, stdout=_comments_page(_page([])))

        transition = trial.walk(threads, _Ask())

        assert transition == done(_Threads(threads=[_open("PRRT_1", 101, 102)]))
        assert trial.shell.commands[1].endswith(f"{_REPO} -f id=PRRT_1 -f after=k1")
        assert trial.shell.commands[2].endswith(f"{_REPO} -f id=PRRT_1 -f after=k2")

    # Without it a full page reads as the whole answer, which is the cut this
    # is here to refuse.
    @staticmethod
    def test_an_answer_that_does_not_say_if_there_is_more(trial: Trial) -> None:
        answer = _threads_page({"nodes": []})
        trial.shell.replies(when=_GRAPHQL, stdout=answer)

        with pytest.raises(ForgeError, match="threads this could not read"):
            trial.walk(threads, _Ask())

    @staticmethod
    def test_more_comments_on_a_thread_that_is_gone(trial: Trial) -> None:
        held = _page([_node("PRRT_1", _page([], cursor="k1"))])
        trial.shell.replies(when=_GRAPHQL, stdout=_threads_page(held))
        trial.shell.replies(when=_GRAPHQL, stdout='{"data": {"node": null}}')

        with pytest.raises(ForgeError, match="comments this could not read"):
            trial.walk(threads, _Ask())

    @staticmethod
    def test_an_answer_that_will_not_parse(trial: Trial) -> None:
        nodes = {"reviewThreads": {"nodes": [{"id": "PRRT_1"}]}}
        answer = {"data": {"repository": {"pullRequest": nodes}}}
        trial.shell.replies(when="slug=*gh api graphql*", stdout=json.dumps(answer))

        with pytest.raises(ForgeError, match="threads this could not read"):
            trial.walk(threads, _Ask())

    # gh exits 0 on this and the answer carries no GraphQL error, so the only
    # thing standing between it and a review posted over everything already
    # raised is that the threads have no default to fall back on.
    @staticmethod
    def test_an_answer_with_no_pull_request_in_it_is_not_no_threads(
        trial: Trial,
    ) -> None:
        answer = {"data": {"repository": {"pullRequest": None}}}
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

        assert trial.walk(anchored, _Ask()) == done(Posted(count=1))
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

        assert trial.walk(general, _Ask()) == done(Posted(count=1))
        assert trial.shell.commands == ["gh pr comment 7 --body hm"]

    # The head commit is the same for every item, so it is asked for once.
    @staticmethod
    def test_a_whole_review_costs_one_head_read(trial: Trial) -> None:
        trial.shell.replies(when="gh pr view 7 --json headRefOid*", stdout="abc123\n")
        trial.shell.replies(when="gh api repos/*", always=True)

        assert trial.walk(several, _Ask()) == done(Posted(count=2))
        head, first, second = trial.shell.commands
        assert head == "gh pr view 7 --json headRefOid -q .headRefOid"
        assert first.endswith("-f body=one")
        assert second.endswith("-f body=two")

    # Nothing raises: what is already up cannot be taken down, so how far it
    # got is the answer and the caller decides about the rest.
    @staticmethod
    def test_an_item_gh_refuses_stops_the_posting_and_says_how_far(
        trial: Trial,
    ) -> None:
        trial.shell.replies(when="gh pr view 7 --json headRefOid*", stdout="abc123\n")
        trial.shell.replies(
            when="gh api repos/*", exit_code=1, stderr="422", always=True
        )
        trial.shell.replies(when="gh pr comment 7 --body one")
        trial.shell.replies(
            when="gh pr comment 7 --body two", exit_code=1, stderr="403"
        )

        assert trial.walk(several, _Ask()) == done(
            Posted(count=1, stopped="could not comment on #7: 403")
        )

    # The anchor is what a head read buys, and losing it is not losing the
    # item: every one of them goes up plainly instead.
    @staticmethod
    def test_a_head_gh_will_not_give_costs_the_anchor_only(trial: Trial) -> None:
        trial.shell.replies(
            when="gh pr view 7 --json headRefOid*", exit_code=1, stderr="404"
        )
        trial.shell.replies(when="gh pr comment 7*")

        assert trial.walk(anchored, _Ask()) == done(Posted(count=1))
        assert trial.shell.commands[-1] == "gh pr comment 7 --body hm"


_OPENED = '{"number": 9, "html_url": "https://github.com/o/r/issues/9"}'
_ID = "gh api repos/{owner}/{repo}/issues/9 --jq .id"
_SUBS = "gh api repos/{owner}/{repo}/issues/7/sub_issues --paginate --jq '.[].number'"
_BLOCKERS = (
    "gh api repos/{owner}/{repo}/issues/7/dependencies/blocked_by"
    " --paginate --jq '.[].number'"
)


class TestIssue:
    @staticmethod
    def test_the_number_and_the_url_come_back(trial: Trial) -> None:
        trial.shell.replies(when="gh api repos*issues -X POST*", stdout=_OPENED)

        assert trial.walk(issue, _Ask()) == done(
            Opened(number=9, url="https://github.com/o/r/issues/9")
        )
        assert trial.shell.commands == [
            (
                "gh api repos/{owner}/{repo}/issues -X POST"
                f" -f title={shlex.quote('a title')}"
                f" -f body={shlex.quote('a body')}"
            )
        ]

    @staticmethod
    def test_an_answer_without_a_number_will_not_do(trial: Trial) -> None:
        trial.shell.replies(when="gh api repos*issues -X POST*", stdout="{}")

        with pytest.raises(ForgeError, match="issue this could not read"):
            trial.walk(issue, _Ask())


class TestLabelIssue:
    @staticmethod
    def test_what_goes_on_and_what_comes_off_in_one_call(trial: Trial) -> None:
        trial.shell.replies(when="gh issue edit*")

        assert trial.walk(label_issue, _Ask()) == done()
        assert trial.shell.commands == [
            "gh issue edit 7 --add-label bug --remove-label epic"
        ]

    @staticmethod
    def test_nothing_to_change_is_no_call(trial: Trial) -> None:
        @step
        async def nothing(ask: _Ask) -> Transition:
            await _FORGE.label_issue(ask.number)
            return done()

        trial.walk(nothing, _Ask())

        assert not trial.shell.commands


class TestLinks:
    @staticmethod
    def test_a_sub_issue_is_attached_by_the_id_behind_its_number(trial: Trial) -> None:
        trial.shell.replies(when=_ID, stdout="1234\n")
        trial.shell.replies(when="gh api repos*sub_issues -X POST*")

        assert trial.walk(attach, _Ask()) == done()
        assert trial.shell.commands == [
            _ID,
            (
                "gh api repos/{owner}/{repo}/issues/7/sub_issues -X POST"
                " -F sub_issue_id=1234"
            ),
        ]

    @staticmethod
    def test_blocked_by_takes_the_blocker_s_id(trial: Trial) -> None:
        trial.shell.replies(when=_ID, stdout="1234\n")
        trial.shell.replies(when="gh api repos*blocked_by -X POST*")

        assert trial.walk(blocks, _Ask()) == done()
        assert trial.shell.commands == [
            _ID,
            (
                "gh api repos/{owner}/{repo}/issues/7/dependencies/blocked_by"
                " -X POST -F issue_id=1234"
            ),
        ]

    # The API refuses a link it already holds, so one that is there is left
    # alone, and a cast run again is not refused on it.
    @staticmethod
    def test_a_sub_issue_already_attached_is_left_alone(trial: Trial) -> None:
        trial.shell.replies(when=_ID, stdout="1234\n")
        trial.shell.replies(
            when="gh api repos*sub_issues -X POST*", exit_code=1, stderr="422"
        )
        trial.shell.replies(when=_SUBS, stdout="3\n9\n")

        assert trial.walk(attach, _Ask()) == done()
        assert trial.shell.commands[-1] == _SUBS

    @staticmethod
    def test_a_blocker_already_linked_is_left_alone(trial: Trial) -> None:
        trial.shell.replies(when=_ID, stdout="1234\n")
        trial.shell.replies(
            when="gh api repos*blocked_by -X POST*", exit_code=1, stderr="422"
        )
        trial.shell.replies(when=_BLOCKERS, stdout="9\n")

        assert trial.walk(blocks, _Ask()) == done()
        assert trial.shell.commands[-1] == _BLOCKERS

    # Refused and not there: what the forge said to the write is the error.
    @staticmethod
    def test_a_refused_link_that_is_not_there_stops_the_link(trial: Trial) -> None:
        trial.shell.replies(when=_ID, stdout="1234\n")
        trial.shell.replies(
            when="gh api repos*blocked_by -X POST*", exit_code=1, stderr="Forbidden"
        )
        trial.shell.replies(when=_BLOCKERS, stdout="3\n")

        with pytest.raises(ForgeError, match="blocked by #9: Forbidden"):
            trial.walk(blocks, _Ask())

    @staticmethod
    def test_links_that_cannot_be_listed_stop_the_link(trial: Trial) -> None:
        trial.shell.replies(when=_ID, stdout="1234\n")
        trial.shell.replies(
            when="gh api repos*blocked_by -X POST*", exit_code=1, stderr="Forbidden"
        )
        trial.shell.replies(when=_BLOCKERS, exit_code=1, stderr="Not Found")

        with pytest.raises(ForgeError, match="could not say #7 is blocked by #9"):
            trial.walk(blocks, _Ask())

    @staticmethod
    def test_a_number_with_no_id_behind_it_stops_the_link(trial: Trial) -> None:
        trial.shell.replies(when=_ID, exit_code=1, stderr="Not Found")

        with pytest.raises(ForgeError, match="could not read the id of #9"):
            trial.walk(attach, _Ask())


_AUTHORED = (
    "gh issue list --author @me --state open --limit 200"
    " --json number,title,url,body,labels"
)
_ASSIGNED = (
    "gh issue list --assignee @me --state open --limit 200"
    " --json number,title,url,body,labels"
)


@step
async def issues(_: _Ask) -> Transition:
    return done(await _FORGE.issues())


def _issue(number: int, **extra: object) -> dict[str, object]:
    return {
        "number": number,
        "title": f"issue {number}",
        "url": f"https://github.com/o/r/issues/{number}",
        "body": "",
        "labels": [],
        **extra,
    }


class TestIssues:
    @staticmethod
    def test_authored_and_assigned_are_merged_once_each_lowest_first(
        trial: Trial,
    ) -> None:
        trial.shell.replies(
            when=_AUTHORED,
            stdout=json.dumps([_issue(9, labels=[{"name": "bug"}]), _issue(4)]),
        )
        trial.shell.replies(when=_ASSIGNED, stdout=json.dumps([_issue(4), _issue(2)]))

        assert trial.walk(issues, _Ask()) == done(
            Listing(
                issues=[
                    Issue(
                        number=2, title="issue 2", url="https://github.com/o/r/issues/2"
                    ),
                    Issue(
                        number=4, title="issue 4", url="https://github.com/o/r/issues/4"
                    ),
                    Issue(
                        number=9,
                        title="issue 9",
                        url="https://github.com/o/r/issues/9",
                        labels=["bug"],
                    ),
                ]
            )
        )
        assert trial.shell.commands == [_AUTHORED, _ASSIGNED]

    # A listing as long as the limit is a listing with no end in sight, and
    # what is past it is never asked for.
    @staticmethod
    def test_a_listing_that_hit_the_limit_says_it_was_cut_short(trial: Trial) -> None:
        rows = [_issue(number) for number in range(1, 201)]
        trial.shell.replies(when=_AUTHORED, stdout=json.dumps(rows))
        trial.shell.replies(when=_ASSIGNED, stdout="[]")

        transition = trial.walk(issues, _Ask())

        assert isinstance(transition, type(done()))
        assert isinstance(transition.result, Listing)
        assert transition.result.truncated
        assert len(transition.result.issues) == len(rows)

    @staticmethod
    def test_a_listing_that_will_not_parse(trial: Trial) -> None:
        trial.shell.replies(when=_AUTHORED, stdout="[{}]")

        with pytest.raises(ForgeError, match="issues this could not read"):
            trial.walk(issues, _Ask())
