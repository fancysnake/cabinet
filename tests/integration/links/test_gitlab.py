"""What is said to glab, and what is made of the answer."""

import json

import pytest
from pydantic import BaseModel
from vekna.lexicon import Transition, done, step
from vekna.trial import Trial

from cabinet.links.forge.gitlab import GitlabForge
from cabinet.pacts.forge import ForgeError
from cabinet.pacts.pulls import Board, Check, PullRequest
from cabinet.pacts.threads import Comment, Finding, Posted, Thread

_FORGE = GitlabForge()

_LIST = (
    "glab api 'projects/:id/merge_requests"
    "?scope=created_by_me&state=opened&per_page=100'"
)
_DISCUSSIONS = "glab api 'projects/:id/merge_requests/7/discussions?per_page=100'"
_STATUSES = "glab api 'projects/:id/repository/commits/feature/statuses?per_page=100'"
_MR = "glab api projects/:id/merge_requests/7"
_THREAD = Thread(
    id="d1",
    resolved=False,
    path="src/thing.py",
    line=12,
    comments=[Comment(id="101", author="reviewer", body="guard this")],
)


def _mr(iid: int, **extra: object) -> dict[str, object]:
    return {
        "iid": iid,
        "title": f"mr {iid}",
        "web_url": f"https://gitlab.example/o/r/-/merge_requests/{iid}",
        "source_branch": f"feature-{iid}",
        "target_branch": "main",
        "updated_at": "2026-08-01T22:00:00Z",
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
    findings = [Finding(path="src/thing.py", line=12, body="hm")]
    return done(await _FORGE.comment(ask.number, findings))


@step
async def general(ask: _Ask) -> Transition:
    return done(await _FORGE.comment(ask.number, [Finding(path="", body="hm")]))


# Two anchored items in one review, which is what the diff refs are read once
# for.
@step
async def several(ask: _Ask) -> Transition:
    findings = [
        Finding(path="src/thing.py", line=12, body="one"),
        Finding(path="src/other.py", line=3, body="two"),
    ]
    return done(await _FORGE.comment(ask.number, findings))


@step
async def issue(_: _Ask) -> Transition:
    return done(_Made(url=await _FORGE.issue("a title", "a body")))


class TestPulls:
    @staticmethod
    def test_merge_requests_become_pull_requests(trial: Trial) -> None:
        trial.shell.replies(
            when=_LIST, stdout=json.dumps([_mr(7, labels=["pr::wait"])])
        )

        assert trial.walk(pulls, _Ask()) == done(
            _Pulls(
                pulls=[
                    PullRequest(
                        number=7,
                        title="mr 7",
                        url="https://gitlab.example/o/r/-/merge_requests/7",
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
    def test_a_glab_that_will_not_answer(trial: Trial) -> None:
        trial.shell.replies(when=_LIST, exit_code=1, stderr="401")

        with pytest.raises(ForgeError, match=r"could not list.*401"):
            trial.walk(pulls, _Ask())

    @staticmethod
    def test_a_listing_that_will_not_parse(trial: Trial) -> None:
        trial.shell.replies(when=_LIST, stdout="[{}]")

        with pytest.raises(ForgeError, match="unreadable"):
            trial.walk(pulls, _Ask())


class TestLabels:
    @staticmethod
    def test_read_off_the_merge_request(trial: Trial) -> None:
        trial.shell.replies(when=_MR, stdout=json.dumps(_mr(7, labels=["bug"])))

        assert trial.walk(labels, _Ask()) == done(_Labels(labels=["bug"]))

    @staticmethod
    def test_labels_that_will_not_parse(trial: Trial) -> None:
        trial.shell.replies(when=_MR, stdout="{}")

        with pytest.raises(ForgeError, match="labels this could not read"):
            trial.walk(labels, _Ask())

    @staticmethod
    def test_both_halves_go_in_one_call(trial: Trial) -> None:
        trial.shell.replies(when="glab mr update 7*")

        trial.walk(label, _Ask())

        assert trial.shell.commands == [
            "glab mr update 7 --label v:refresh:started --unlabel v:refresh:done"
        ]

    @staticmethod
    def test_nothing_to_change_is_no_call(trial: Trial) -> None:
        @step
        async def nothing(ask: _Ask) -> Transition:
            await _FORGE.label(ask.number)
            return done()

        trial.walk(nothing, _Ask())

        assert not trial.shell.commands


class TestThreads:
    @staticmethod
    def test_resolvable_discussions_become_threads(trial: Trial) -> None:
        answer = [
            {
                "id": "d1",
                "notes": [
                    {
                        "id": 101,
                        "body": "guard this",
                        "author": {"username": "reviewer"},
                        "resolvable": True,
                        "resolved": False,
                        "position": {"new_path": "src/thing.py", "new_line": 12},
                    }
                ],
            },
            {"id": "d2", "notes": [{"id": 102, "body": "changed the title"}]},
        ]
        trial.shell.replies(when=_DISCUSSIONS, stdout=json.dumps(answer))

        assert trial.walk(threads, _Ask()) == done(_Threads(threads=[_THREAD]))

    @staticmethod
    def test_discussions_that_will_not_parse(trial: Trial) -> None:
        trial.shell.replies(when=_DISCUSSIONS, stdout='[{"notes": []}]')

        with pytest.raises(ForgeError, match="discussions this could not read"):
            trial.walk(threads, _Ask())

    @staticmethod
    def test_a_reply_is_a_note_on_the_discussion(trial: Trial) -> None:
        trial.shell.replies(when="glab api *")

        trial.walk(reply, _Ask())

        assert trial.shell.commands == [
            (
                "glab api projects/:id/merge_requests/7/discussions/d1/notes"
                " -X POST -f body=done"
            )
        ]

    @staticmethod
    def test_resolving_is_a_put(trial: Trial) -> None:
        trial.shell.replies(when="glab api *")

        trial.walk(resolve, _Ask())

        assert trial.shell.commands == [
            (
                "glab api projects/:id/merge_requests/7/discussions/d1 -X PUT"
                " -F resolved=true"
            )
        ]


class TestBoard:
    @staticmethod
    def test_statuses_become_checks(trial: Trial) -> None:
        answer = [
            {"name": "test", "status": "success"},
            {"name": "checks", "status": "failed"},
            {"name": "lint", "status": "canceled"},
            {"name": "codecov/patch", "status": "running", "description": "96% hit"},
        ]
        trial.shell.replies(when=_STATUSES, stdout=json.dumps(answer))

        assert trial.walk(board, _Ask()) == done(
            Board(
                checks=[
                    Check(name="test", passed=True),
                    Check(name="checks", passed=False),
                    Check(name="lint", passed=False),
                    Check(name="codecov/patch", title="96% hit"),
                ]
            )
        )

    @staticmethod
    def test_a_full_page_may_be_short(trial: Trial) -> None:
        full = [{"name": f"job{index}", "status": "success"} for index in range(100)]
        trial.shell.replies(when=_STATUSES, stdout=json.dumps(full))

        transition = trial.walk(board, _Ask())

        assert isinstance(transition, type(done()))
        assert transition.result is not None
        assert transition.result == Board(
            checks=[Check(name=f"job{index}", passed=True) for index in range(100)],
            truncated=True,
        )

    @staticmethod
    def test_statuses_that_will_not_parse(trial: Trial) -> None:
        trial.shell.replies(when=_STATUSES, stdout='[{"name": 1}]')

        with pytest.raises(ForgeError, match="statuses this could not read"):
            trial.walk(board, _Ask())


class TestComment:
    @staticmethod
    def test_an_anchored_item_is_a_positioned_discussion(trial: Trial) -> None:
        refs = {"diff_refs": {"base_sha": "b", "head_sha": "h", "start_sha": "s"}}
        trial.shell.replies(when=_MR, stdout=json.dumps(refs))
        trial.shell.replies(when="glab api projects/:id/merge_requests/7/discussions*")

        assert trial.walk(anchored, _Ask()) == done(Posted(count=1))
        assert trial.shell.commands[-1] == (
            "glab api projects/:id/merge_requests/7/discussions -X POST -f body=hm"
            " -f 'position[position_type]=text' -f 'position[base_sha]=b'"
            " -f 'position[head_sha]=h' -f 'position[start_sha]=s'"
            " -f position[new_path]=src/thing.py -f position[old_path]=src/thing.py"
            " -F 'position[new_line]=12'"
        )

    @staticmethod
    def test_a_refused_position_falls_back_to_a_note(trial: Trial) -> None:
        refs = {"diff_refs": {"base_sha": "b", "head_sha": "h", "start_sha": "s"}}
        trial.shell.replies(when=_MR, stdout=json.dumps(refs))
        trial.shell.replies(
            when="glab api projects/:id/merge_requests/7/discussions*",
            exit_code=1,
            stderr="400",
        )
        trial.shell.replies(when="glab mr note 7*")

        trial.walk(anchored, _Ask())

        assert trial.shell.commands[-1] == "glab mr note 7 -m hm"

    @staticmethod
    def test_a_general_item_is_a_note(trial: Trial) -> None:
        trial.shell.replies(when="glab mr note 7*")

        assert trial.walk(general, _Ask()) == done(Posted(count=1))
        assert trial.shell.commands == ["glab mr note 7 -m hm"]

    # The refs are the same for every item, so they are read once.
    @staticmethod
    def test_a_whole_review_costs_one_refs_read(trial: Trial) -> None:
        refs = {"diff_refs": {"base_sha": "b", "head_sha": "h", "start_sha": "s"}}
        trial.shell.replies(when=_MR, stdout=json.dumps(refs))
        trial.shell.replies(
            when="glab api projects/:id/merge_requests/7/discussions*", always=True
        )

        assert trial.walk(several, _Ask()) == done(Posted(count=2))
        refs_read, first, second = trial.shell.commands
        assert refs_read == _MR
        assert first.endswith("-F 'position[new_line]=12'")
        assert second.endswith("-F 'position[new_line]=3'")

    # Nothing raises: what is already up cannot be taken down, so how far it
    # got is the answer and the caller decides about the rest.
    @staticmethod
    def test_an_item_glab_refuses_stops_the_posting_and_says_how_far(
        trial: Trial,
    ) -> None:
        refs = {"diff_refs": {"base_sha": "b", "head_sha": "h", "start_sha": "s"}}
        trial.shell.replies(when=_MR, stdout=json.dumps(refs))
        trial.shell.replies(
            when="glab api projects/:id/merge_requests/7/discussions*",
            exit_code=1,
            stderr="400",
            always=True,
        )
        trial.shell.replies(when="glab mr note 7 -m one")
        trial.shell.replies(when="glab mr note 7 -m two", exit_code=1, stderr="403")

        assert trial.walk(several, _Ask()) == done(
            Posted(count=1, stopped="could not comment on !7: 403")
        )

    # The anchor is what the refs buy, and losing it is not losing the item.
    @staticmethod
    def test_a_merge_request_that_will_not_parse_costs_the_anchor_only(
        trial: Trial,
    ) -> None:
        trial.shell.replies(when=_MR, stdout="{}")
        trial.shell.replies(when="glab mr note 7*")

        assert trial.walk(anchored, _Ask()) == done(Posted(count=1))
        assert trial.shell.commands[-1] == "glab mr note 7 -m hm"


class TestIssue:
    @staticmethod
    def test_the_url_is_read_off_the_answer(trial: Trial) -> None:
        trial.shell.replies(
            when="glab api projects/:id/issues*",
            stdout='{"web_url": "https://gitlab.example/o/r/-/issues/9"}',
        )

        assert trial.walk(issue, _Ask()) == done(
            _Made(url="https://gitlab.example/o/r/-/issues/9")
        )
        assert trial.shell.commands == [
            (
                "glab api projects/:id/issues -X POST -f title='a title'"
                " -f description='a body'"
            )
        ]

    @staticmethod
    def test_an_answer_without_a_url(trial: Trial) -> None:
        trial.shell.replies(when="glab api projects/:id/issues*", stdout="{}")

        with pytest.raises(ForgeError, match="issue this could not read"):
            trial.walk(issue, _Ask())
