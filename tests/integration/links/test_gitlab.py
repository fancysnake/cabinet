"""What is said to glab, and what is made of the answer."""

import json
from collections.abc import Iterable

import pytest
from vekna.trial import Trial

from cabinet.links.forge.gitlab import GitlabForge
from cabinet.pacts.forge import ForgeError
from cabinet.pacts.issues import Issue, Listing, Opened
from cabinet.pacts.pulls import Board, Check, PullRequest
from cabinet.pacts.threads import Comment, Finding, Posted, Thread
from tests.conftest import drive

_FORGE = GitlabForge()

_LIST = (
    "glab api 'projects/:id/merge_requests"
    "?scope=created_by_me&state=opened&per_page=100'"
)
_DISCUSSIONS = (
    "glab api 'projects/:id/merge_requests/7/discussions?per_page=100&page=1'"
)
_SECOND = "glab api 'projects/:id/merge_requests/7/discussions?per_page=100&page=2'"
_STATUSES = "glab api 'projects/:id/repository/commits/feature/statuses?per_page=100'"
_MR = "glab api projects/:id/merge_requests/7"
_THREAD = Thread(
    id="d1",
    resolved=False,
    path="src/thing.py",
    line=12,
    comments=[Comment(id="101", author="reviewer", body="guard this")],
)
_ANCHORED = [Finding(path="src/thing.py", line=12, body="hm")]
# Two anchored items in one review, which is what the diff refs are read once
# for.
_SEVERAL = [
    Finding(path="src/thing.py", line=12, body="one"),
    Finding(path="src/other.py", line=3, body="two"),
]


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


# Open discussions, one note each, numbered by `numbers`.
def _discussions(numbers: Iterable[int]) -> str:
    return json.dumps(
        [
            {"id": f"d{one}", "notes": [{"id": one, "resolvable": True}]}
            for one in numbers
        ]
    )


def _opened(numbers: Iterable[int]) -> list[Thread]:
    return [
        Thread(
            id=f"d{one}",
            resolved=False,
            comments=[Comment(id=str(one), author="", body="")],
        )
        for one in numbers
    ]


class TestPulls:
    @staticmethod
    def test_merge_requests_become_pull_requests(trial: Trial) -> None:
        trial.shell.replies(
            when=_LIST, stdout=json.dumps([_mr(7, labels=["pr::wait"])])
        )

        assert drive(trial, _FORGE.pulls) == [
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
        assert trial.shell.commands == [_LIST]

    @staticmethod
    def test_a_glab_that_will_not_answer(trial: Trial) -> None:
        trial.shell.replies(when=_LIST, exit_code=1, stderr="401")

        with pytest.raises(ForgeError, match=r"could not list.*401"):
            drive(trial, _FORGE.pulls)

    @staticmethod
    def test_a_listing_that_will_not_parse(trial: Trial) -> None:
        trial.shell.replies(when=_LIST, stdout="[{}]")

        with pytest.raises(ForgeError, match="merge requests this could not read"):
            drive(trial, _FORGE.pulls)


class TestLabels:
    @staticmethod
    def test_read_off_the_merge_request(trial: Trial) -> None:
        trial.shell.replies(when=_MR, stdout=json.dumps(_mr(7, labels=["bug"])))

        assert drive(trial, lambda: _FORGE.labels(7)) == ["bug"]

    @staticmethod
    def test_labels_that_will_not_parse(trial: Trial) -> None:
        trial.shell.replies(when=_MR, stdout="{}")

        with pytest.raises(ForgeError, match="labels this could not read"):
            drive(trial, lambda: _FORGE.labels(7))

    @staticmethod
    def test_both_halves_go_in_one_call(trial: Trial) -> None:
        trial.shell.replies(when="glab mr update 7*")

        drive(
            trial,
            lambda: _FORGE.label(
                7, add=["v:refresh:started"], remove=["v:refresh:done"]
            ),
        )

        assert trial.shell.commands == [
            "glab mr update 7 --label v:refresh:started --unlabel v:refresh:done"
        ]

    @staticmethod
    def test_nothing_to_change_is_no_call(trial: Trial) -> None:
        drive(trial, lambda: _FORGE.label(7))

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

        assert drive(trial, lambda: _FORGE.threads(7)) == [_THREAD]

    @staticmethod
    def test_discussions_past_a_full_page_are_asked_for(trial: Trial) -> None:
        trial.shell.replies(when=_DISCUSSIONS, stdout=_discussions(range(100)))
        trial.shell.replies(when=_SECOND, stdout=_discussions([100]))

        assert drive(trial, lambda: _FORGE.threads(7)) == _opened(range(101))
        assert trial.shell.commands == [_DISCUSSIONS, _SECOND]

    # The next-page headers go unread, so a full last page costs one
    # more ask, which comes back empty.
    @staticmethod
    def test_an_exactly_full_last_page(trial: Trial) -> None:
        trial.shell.replies(when=_DISCUSSIONS, stdout=_discussions(range(100)))
        trial.shell.replies(when=_SECOND, stdout="[]")

        assert drive(trial, lambda: _FORGE.threads(7)) == _opened(range(100))
        assert trial.shell.commands == [_DISCUSSIONS, _SECOND]

    @staticmethod
    def test_a_short_page_is_the_last(trial: Trial) -> None:
        trial.shell.replies(when=_DISCUSSIONS, stdout=_discussions(range(3)))

        assert drive(trial, lambda: _FORGE.threads(7)) == _opened(range(3))
        assert trial.shell.commands == [_DISCUSSIONS]

    @staticmethod
    def test_discussions_that_will_not_parse(trial: Trial) -> None:
        trial.shell.replies(when=_DISCUSSIONS, stdout='[{"notes": []}]')

        with pytest.raises(ForgeError, match="discussions this could not read"):
            drive(trial, lambda: _FORGE.threads(7))

    @staticmethod
    def test_a_reply_is_a_note_on_the_discussion(trial: Trial) -> None:
        trial.shell.replies(when="glab api *")

        drive(trial, lambda: _FORGE.reply(7, _THREAD, "done"))

        assert trial.shell.commands == [
            (
                "glab api projects/:id/merge_requests/7/discussions/d1/notes"
                " -X POST -f body=done"
            )
        ]

    @staticmethod
    def test_resolving_is_a_put(trial: Trial) -> None:
        trial.shell.replies(when="glab api *")

        drive(trial, lambda: _FORGE.resolve(7, _THREAD))

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

        assert drive(trial, lambda: _FORGE.board("feature")) == Board(
            checks=[
                Check(name="test", passed=True),
                Check(name="checks", passed=False),
                Check(name="lint", passed=False),
                Check(name="codecov/patch", title="96% hit"),
            ]
        )

    @staticmethod
    def test_a_full_page_may_be_short(trial: Trial) -> None:
        full = [{"name": f"job{index}", "status": "success"} for index in range(100)]
        trial.shell.replies(when=_STATUSES, stdout=json.dumps(full))

        assert drive(trial, lambda: _FORGE.board("feature")) == Board(
            checks=[Check(name=f"job{index}", passed=True) for index in range(100)],
            truncated=True,
        )

    @staticmethod
    def test_statuses_that_will_not_parse(trial: Trial) -> None:
        trial.shell.replies(when=_STATUSES, stdout='[{"name": 1}]')

        with pytest.raises(ForgeError, match="statuses this could not read"):
            drive(trial, lambda: _FORGE.board("feature"))


class TestComment:
    @staticmethod
    def test_an_anchored_item_is_a_positioned_discussion(trial: Trial) -> None:
        refs = {"diff_refs": {"base_sha": "b", "head_sha": "h", "start_sha": "s"}}
        trial.shell.replies(when=_MR, stdout=json.dumps(refs))
        trial.shell.replies(when="glab api projects/:id/merge_requests/7/discussions*")

        assert drive(trial, lambda: _FORGE.comment(7, _ANCHORED)) == Posted(count=1)
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

        drive(trial, lambda: _FORGE.comment(7, _ANCHORED))

        assert trial.shell.commands[-1] == "glab mr note 7 -m hm"

    @staticmethod
    def test_a_general_item_is_a_note(trial: Trial) -> None:
        trial.shell.replies(when="glab mr note 7*")
        general = [Finding(path="", body="hm")]

        assert drive(trial, lambda: _FORGE.comment(7, general)) == Posted(count=1)
        assert trial.shell.commands == ["glab mr note 7 -m hm"]

    # The refs are the same for every item, so they are read once.
    @staticmethod
    def test_a_whole_review_costs_one_refs_read(trial: Trial) -> None:
        refs = {"diff_refs": {"base_sha": "b", "head_sha": "h", "start_sha": "s"}}
        trial.shell.replies(when=_MR, stdout=json.dumps(refs))
        trial.shell.replies(
            when="glab api projects/:id/merge_requests/7/discussions*", always=True
        )

        assert drive(trial, lambda: _FORGE.comment(7, _SEVERAL)) == Posted(count=2)
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

        assert drive(trial, lambda: _FORGE.comment(7, _SEVERAL)) == Posted(
            count=1, stopped="could not comment on !7: 403"
        )

    # The anchor is what the refs buy, and losing it is not losing the item.
    @staticmethod
    def test_a_merge_request_that_will_not_parse_costs_the_anchor_only(
        trial: Trial,
    ) -> None:
        trial.shell.replies(when=_MR, stdout="{}")
        trial.shell.replies(when="glab mr note 7*")

        assert drive(trial, lambda: _FORGE.comment(7, _ANCHORED)) == Posted(count=1)
        assert trial.shell.commands[-1] == "glab mr note 7 -m hm"


_PROJECT = "glab api projects/:id"
_LINKS = "glab api projects/:id/issues/7/links"
_LISTED = "glab api 'projects/:id/issues/7/links?per_page=100'"


class TestIssue:
    @staticmethod
    def test_the_number_and_the_url_are_read_off_the_answer(trial: Trial) -> None:
        trial.shell.replies(
            when="glab api projects/:id/issues -X POST*",
            stdout='{"iid": 9, "web_url": "https://gitlab.example/o/r/-/issues/9"}',
        )

        assert drive(trial, lambda: _FORGE.issue("a title", "a body")) == Opened(
            number=9, url="https://gitlab.example/o/r/-/issues/9"
        )
        assert trial.shell.commands == [
            (
                "glab api projects/:id/issues -X POST -f title='a title'"
                " -f description='a body'"
            )
        ]

    @staticmethod
    def test_an_answer_without_a_url(trial: Trial) -> None:
        trial.shell.replies(when="glab api projects/:id/issues -X POST*", stdout="{}")

        with pytest.raises(ForgeError, match="issue this could not read"):
            drive(trial, lambda: _FORGE.issue("a title", "a body"))


class TestLabelIssue:
    @staticmethod
    def test_what_goes_on_and_what_comes_off_in_one_call(trial: Trial) -> None:
        trial.shell.replies(when="glab issue update*")

        drive(trial, lambda: _FORGE.label_issue(7, add=["bug"], remove=["epic"]))

        assert trial.shell.commands == [
            "glab issue update 7 --label bug --unlabel epic"
        ]

    @staticmethod
    def test_nothing_to_change_is_no_call(trial: Trial) -> None:
        drive(trial, lambda: _FORGE.label_issue(7))

        assert not trial.shell.commands


class TestLinks:
    @staticmethod
    def test_a_sub_issue_is_a_relation_with_the_project_spelled_out(
        trial: Trial,
    ) -> None:
        trial.shell.replies(when=_PROJECT, stdout='{"id": 42}')
        trial.shell.replies(when=f"{_LINKS} -X POST*")

        drive(trial, lambda: _FORGE.attach(7, 9))

        assert trial.shell.commands == [
            _PROJECT,
            (
                f"{_LINKS} -X POST -F target_project_id=42 -F target_issue_iid=9"
                " -f link_type=relates_to"
            ),
        ]

    @staticmethod
    def test_blocked_by_is_the_same_endpoint_with_its_own_link_type(
        trial: Trial,
    ) -> None:
        trial.shell.replies(when=_PROJECT, stdout='{"id": 42}')
        trial.shell.replies(when=f"{_LINKS} -X POST*")

        drive(trial, lambda: _FORGE.blocks(7, 9))

        assert trial.shell.commands[-1] == (
            f"{_LINKS} -X POST -F target_project_id=42 -F target_issue_iid=9"
            " -f link_type=is_blocked_by"
        )

    # The API refuses a link it already holds, so one that is there is left
    # alone, and a cast run again is not refused on it.
    @staticmethod
    def test_a_link_already_there_is_left_alone(trial: Trial) -> None:
        trial.shell.replies(when=_PROJECT, stdout='{"id": 42}')
        trial.shell.replies(when=f"{_LINKS} -X POST*", exit_code=1, stderr="409")
        trial.shell.replies(
            when=_LISTED,
            stdout='[{"project_id": 42, "iid": 9, "link_type": "is_blocked_by"}]',
        )

        drive(trial, lambda: _FORGE.blocks(7, 9))

        assert trial.shell.commands[-1] == _LISTED

    # Related to #9 already, or blocked by a #9 of another project: neither is
    # the link asked for, so the refusal stands.
    @staticmethod
    @pytest.mark.parametrize(
        "held",
        [
            '[{"project_id": 42, "iid": 9, "link_type": "relates_to"}]',
            '[{"project_id": 41, "iid": 9, "link_type": "is_blocked_by"}]',
        ],
    )
    def test_a_refused_link_that_is_not_there_stops_the_link(
        trial: Trial, held: str
    ) -> None:
        trial.shell.replies(when=_PROJECT, stdout='{"id": 42}')
        trial.shell.replies(when=f"{_LINKS} -X POST*", exit_code=1, stderr="Forbidden")
        trial.shell.replies(when=_LISTED, stdout=held)

        with pytest.raises(ForgeError, match="blocked by #9: Forbidden"):
            drive(trial, lambda: _FORGE.blocks(7, 9))

    @staticmethod
    def test_links_it_cannot_read_stop_the_link(trial: Trial) -> None:
        trial.shell.replies(when=_PROJECT, stdout='{"id": 42}')
        trial.shell.replies(when=f"{_LINKS} -X POST*", exit_code=1, stderr="409")
        trial.shell.replies(when=_LISTED, stdout="{}")

        with pytest.raises(ForgeError, match="links this could not read"):
            drive(trial, lambda: _FORGE.attach(7, 9))

    @staticmethod
    def test_a_project_that_will_not_say_its_id_stops_the_link(trial: Trial) -> None:
        trial.shell.replies(when=_PROJECT, stdout="{}")

        with pytest.raises(ForgeError, match="project this could not read"):
            drive(trial, lambda: _FORGE.attach(7, 9))


_AUTHORED = (
    "glab api 'projects/:id/issues?state=opened&scope=created_by_me&per_page=100'"
)
_ASSIGNED = (
    "glab api 'projects/:id/issues?state=opened&scope=assigned_to_me&per_page=100'"
)


def _listed(iid: int, **extra: object) -> dict[str, object]:
    return {
        "iid": iid,
        "title": f"issue {iid}",
        "web_url": f"https://gitlab.example/o/r/-/issues/{iid}",
        "description": None,
        "labels": [],
        **extra,
    }


class TestIssues:
    @staticmethod
    def test_created_and_assigned_are_merged_once_each_lowest_first(
        trial: Trial,
    ) -> None:
        nine = _listed(9, description="why", labels=["S"], author={"username": "me"})
        trial.shell.replies(when=_AUTHORED, stdout=json.dumps([nine]))
        trial.shell.replies(when=_ASSIGNED, stdout=json.dumps([nine, _listed(2)]))

        assert drive(trial, _FORGE.issues) == Listing(
            issues=[
                Issue(
                    number=2,
                    title="issue 2",
                    url="https://gitlab.example/o/r/-/issues/2",
                ),
                Issue(
                    number=9,
                    title="issue 9",
                    url="https://gitlab.example/o/r/-/issues/9",
                    body="why",
                    labels=["S"],
                    author="me",
                ),
            ]
        )
        assert trial.shell.commands == [_AUTHORED, _ASSIGNED]

    # A full page may be a short page, as it is for the board.
    @staticmethod
    def test_a_full_page_says_the_listing_was_cut_short(trial: Trial) -> None:
        trial.shell.replies(
            when=_AUTHORED, stdout=json.dumps([_listed(iid) for iid in range(1, 101)])
        )
        trial.shell.replies(when=_ASSIGNED, stdout="[]")

        assert drive(trial, _FORGE.issues).truncated

    @staticmethod
    def test_a_listing_that_will_not_parse(trial: Trial) -> None:
        trial.shell.replies(when=_AUTHORED, stdout="[{}]")

        with pytest.raises(ForgeError, match="issues this could not read"):
            drive(trial, _FORGE.issues)


_USER = "glab api user"


class TestOperator:
    @staticmethod
    def test_the_username_glab_is_using(trial: Trial) -> None:
        trial.shell.replies(when=_USER, stdout=json.dumps({"username": "me"}))

        assert drive(trial, _FORGE.operator) == "me"

    @staticmethod
    def test_no_username_stops_the_link(trial: Trial) -> None:
        trial.shell.replies(when=_USER, stdout="{}")

        with pytest.raises(ForgeError, match="you are nobody"):
            drive(trial, _FORGE.operator)
