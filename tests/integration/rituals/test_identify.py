"""Identifying your issues a page at a time, with one agent session for them all."""

import json

import pytest
from vekna.lexicon import Done, RitualError
from vekna.trial import Trial

from cabinet.gates.ritual.vekna.identify import gather, identify_page, leaf, pin, tally
from cabinet.pacts.identify import Gather, Leaf, Tally
from cabinet.pacts.issues import (
    Identification,
    Identified,
    IdentifiedItem,
    Identify,
    Identifying,
    Issue,
    Page,
    Part,
    Pinning,
)
from cabinet.pacts.project import Project
from cabinet.rituals.identify import identify

_AUTHORED = (
    "gh issue list --author @me --state open --limit 200"
    " --json number,title,url,body,labels"
)
_ASSIGNED = (
    "gh issue list --assignee @me --state open --limit 200"
    " --json number,title,url,body,labels"
)


def _row(number: int, *labels: str) -> dict[str, object]:
    return {
        "number": number,
        "title": f"issue {number}",
        "url": f"https://github.com/o/r/issues/{number}",
        "body": "",
        "labels": [{"name": name} for name in labels],
    }


def _issue(number: int) -> Issue:
    return Issue(
        number=number,
        title=f"issue {number}",
        url=f"https://github.com/o/r/issues/{number}",
    )


def _item(number: int) -> IdentifiedItem:
    return IdentifiedItem(number=number, kind="feature", size="S")


def _labelled(number: int) -> str:
    return f"gh issue edit {number} --add-label feature --add-label S"


def _identified(*numbers: int) -> list[Identification]:
    return [
        Identification(number=number, outcome="identified", item=_item(number))
        for number in numbers
    ]


class TestGather:
    @staticmethod
    def test_only_the_unidentified_are_queued(trial: Trial, project: Project) -> None:
        trial.shell.replies(
            when=_AUTHORED,
            stdout=json.dumps([_row(1, "bug", "S"), _row(2, "bug"), _row(3)]),
        )
        trial.shell.replies(when=_ASSIGNED, stdout="[]")

        transition = trial.walk(gather, Gather(project=project))

        assert isinstance(transition, Leaf)
        assert [one.number for one in transition.queue] == [2, 3]
        assert not transition.truncated

    # A backlog the forge would not list the end of: the queue is what was
    # seen, and the cast says so rather than reading it as the whole of it.
    @staticmethod
    def test_a_listing_cut_short_is_carried_into_the_report(
        trial: Trial, project: Project
    ) -> None:
        trial.shell.replies(
            when=_AUTHORED,
            stdout=json.dumps([_row(number) for number in range(1, 201)]),
        )
        trial.shell.replies(when=_ASSIGNED, stdout="[]")

        transition = trial.walk(gather, Gather(project=project))

        assert isinstance(transition, Leaf)
        assert transition.truncated

    @staticmethod
    def test_a_forge_that_will_not_list_stops_the_cast_with_the_report(
        trial: Trial, project: Project
    ) -> None:
        trial.shell.replies(when=_AUTHORED, exit_code=1, stderr="not logged in")

        transition = trial.walk(gather, Gather(project=project))

        assert isinstance(transition, Tally)
        assert "not logged in" in transition.stopped


class TestLeaf:
    @staticmethod
    def test_the_next_page_is_shown_and_taken_unasked(
        trial: Trial, project: Project
    ) -> None:
        identifying = Leaf(
            project=project, batch=2, queue=[_issue(1), _issue(2), _issue(3)]
        )

        transition = trial.walk(leaf, identifying)

        assert transition == Page(
            identifying=identifying.but(queue=[_issue(3)]),
            issues=[_issue(1), _issue(2)],
        )
        assert trial.deltas == ["  #1 issue 1\n  #2 issue 2"]


class TestIdentifyPage:
    @staticmethod
    def test_the_reading_goes_to_the_forge_writes(
        trial: Trial, project: Project
    ) -> None:
        trial.coding.replies(Identified(items=[_item(1)]))
        page = Page(identifying=Identifying(project=project), issues=[_issue(1)])

        transition = trial.walk(identify_page, page)

        assert transition == Pinning(page=page, items=[_item(1)])

    # An issue the agent invented is not on the page, so nothing is put on it.
    @staticmethod
    def test_an_issue_that_was_never_on_the_page_is_dropped(
        trial: Trial, project: Project
    ) -> None:
        trial.coding.replies(Identified(items=[_item(1), _item(99)]))
        page = Page(identifying=Identifying(project=project), issues=[_issue(1)])

        transition = trial.walk(identify_page, page)

        assert isinstance(transition, Pinning)
        assert transition.items == [_item(1)]

    @staticmethod
    def test_the_agent_only_reads_and_reaches_no_forge(
        trial: Trial, project: Project
    ) -> None:
        trial.coding.replies(Identified(items=[_item(1)]))

        trial.walk(
            identify_page,
            Page(identifying=Identifying(project=project), issues=[_issue(1)]),
        )

        focus = trial.coding.calls[0].focus_options
        options = str(focus)
        assert {"Bash(gh:*)", "Bash(glab:*)"} <= set(focus.disallowed_tools)
        assert "Edit" not in focus.allowed_tools
        assert "permission_mode='dontAsk'" in options
        assert not trial.shell.commands

    @staticmethod
    def test_an_answer_out_of_shape_stops_the_cast_with_the_page_rowed(
        trial: Trial, project: Project
    ) -> None:
        trial.coding.replies("no idea, sorry")
        page = Page(identifying=Identifying(project=project), issues=[_issue(1)])

        transition = trial.walk(identify_page, page)

        assert isinstance(transition, Tally)
        assert transition.identified == [Identification(number=1, outcome="stopped")]
        assert "shape" in transition.stopped


class TestPin:
    @staticmethod
    def test_the_labels_go_on_and_the_page_is_rowed(
        trial: Trial, project: Project
    ) -> None:
        trial.shell.replies(when=_labelled(1))
        page = Page(identifying=Identifying(project=project), issues=[_issue(1)])

        transition = trial.walk(pin, Pinning(page=page, items=[_item(1)]))

        assert transition == Leaf(
            project=project, briefed=True, identified=_identified(1)
        )
        assert trial.shell.commands == [_labelled(1)]

    # An epic wears the epic label in place of a size, and its parts are
    # opened, labelled and attached — the numbers coming back from the forge.
    @staticmethod
    def test_an_epic_is_split_labelled_and_attached(
        trial: Trial, project: Project
    ) -> None:
        trial.shell.replies(when="gh issue edit 1 --add-label edit --add-label epic")
        trial.shell.replies(
            when="gh api repos/{owner}/{repo}/issues -X POST*",
            stdout='{"number": 10, "html_url": "https://github.com/o/r/issues/10"}',
        )
        trial.shell.replies(when=_labelled(10))
        trial.shell.replies(
            when="gh api repos/{owner}/{repo}/issues/10 --jq .id", stdout="99"
        )
        trial.shell.replies(
            when="gh api repos/{owner}/{repo}/issues/1/sub_issues*", always=True
        )
        item = IdentifiedItem(
            number=1,
            kind="edit",
            epic=True,
            parts=[Part(title="first half", body="why", kind="feature", size="S")],
        )
        page = Page(identifying=Identifying(project=project), issues=[_issue(1)])

        transition = trial.walk(pin, Pinning(page=page, items=[item]))

        assert isinstance(transition, Leaf)
        assert transition.identified == [
            Identification(number=1, outcome="identified", item=item, opened=[10])
        ]
        assert trial.shell.commands[-1] == (
            "gh api repos/{owner}/{repo}/issues/1/sub_issues -X POST -F sub_issue_id=99"
        )

    # An issue already part of the epic is attached rather than opened again,
    # and what blocks this one is recorded the same way round.
    @staticmethod
    def test_existing_issues_are_attached_and_blockers_recorded(
        trial: Trial, project: Project
    ) -> None:
        trial.shell.replies(when=_labelled(1))
        trial.shell.replies(
            when="gh api repos*issues/*--jq .id", stdout="99", always=True
        )
        trial.shell.replies(when="gh api repos*sub_issues*", always=True)
        trial.shell.replies(when="gh api repos*blocked_by*", always=True)
        item = IdentifiedItem(
            number=1, kind="feature", size="S", children=[8], blocked_by=[9]
        )
        page = Page(identifying=Identifying(project=project), issues=[_issue(1)])

        transition = trial.walk(pin, Pinning(page=page, items=[item]))

        assert isinstance(transition, Leaf)
        assert trial.shell.commands[2].endswith("sub_issues -X POST -F sub_issue_id=99")
        assert trial.shell.commands[4].endswith("blocked_by -X POST -F issue_id=99")

    @staticmethod
    def test_an_issue_the_agent_did_not_answer_for_is_named(
        trial: Trial, project: Project
    ) -> None:
        trial.shell.replies(when=_labelled(1))
        page = Page(
            identifying=Identifying(project=project), issues=[_issue(1), _issue(2)]
        )

        transition = trial.walk(pin, Pinning(page=page, items=[_item(1)]))

        assert transition == Leaf(
            project=project,
            briefed=True,
            identified=[*_identified(1), Identification(number=2, outcome="missed")],
        )

    # A refusal is named on its own issue, and the issues after it are still
    # labelled.
    @staticmethod
    def test_a_forge_that_refuses_mid_page_goes_on(
        trial: Trial, project: Project
    ) -> None:
        trial.shell.replies(when=_labelled(1))
        trial.shell.replies(when=_labelled(2), exit_code=1, stderr="no such label")
        trial.shell.replies(when=_labelled(3))
        page = Page(
            identifying=Identifying(project=project),
            issues=[_issue(1), _issue(2), _issue(3)],
        )

        transition = trial.walk(
            pin, Pinning(page=page, items=[_item(1), _item(2), _item(3)])
        )

        assert transition == Leaf(
            project=project,
            briefed=True,
            identified=[
                *_identified(1),
                Identification(
                    number=2,
                    outcome="identified",
                    item=_item(2),
                    refused=["could not label #2: no such label"],
                ),
                *_identified(3),
            ],
        )

    # Every write on the page refused is a forge that is down or will not have
    # you, and the cast stops there rather than refusing its way through the
    # backlog to a clean exit.
    @staticmethod
    def test_a_page_with_every_write_refused_stops_the_cast(
        trial: Trial, project: Project
    ) -> None:
        trial.shell.replies(
            when="gh issue edit*", exit_code=1, stderr="auth expired", always=True
        )
        page = Page(
            identifying=Identifying(project=project, queue=[_issue(3)]),
            issues=[_issue(1), _issue(2)],
        )

        transition = trial.walk(pin, Pinning(page=page, items=[_item(1), _item(2)]))

        assert transition == Tally(
            project=project,
            queue=[_issue(3)],
            briefed=True,
            identified=[
                Identification(
                    number=number,
                    outcome="identified",
                    item=_item(number),
                    refused=[f"could not label #{number}: auth expired"],
                )
                for number in (1, 2)
            ],
            stopped=(
                "the forge refused every write on the page, first:"
                " could not label #1: auth expired"
            ),
        )

    # A link the forge refuses is named like any other write, and the
    # rest of the issue's links still go on.
    @staticmethod
    def test_a_refused_blocker_leaves_the_other_links_on(
        trial: Trial, project: Project
    ) -> None:
        trial.shell.replies(when=_labelled(1))
        trial.shell.replies(
            when="gh api repos*issues/*--jq .id", stdout="99", always=True
        )
        trial.shell.replies(
            when="gh api repos*blocked_by*", exit_code=1, stderr="Not Found"
        )
        trial.shell.replies(when="gh api repos*blocked_by*", always=True)
        item = IdentifiedItem(number=1, kind="feature", size="S", blocked_by=[6, 7])
        page = Page(identifying=Identifying(project=project), issues=[_issue(1)])

        transition = trial.walk(pin, Pinning(page=page, items=[item]))

        assert isinstance(transition, Leaf)
        assert transition.identified == [
            Identification(
                number=1,
                outcome="identified",
                item=item,
                refused=["could not say #1 is blocked by #6: Not Found"],
            )
        ]
        assert trial.shell.commands[-1].endswith("blocked_by -X POST -F issue_id=99")

    # A part the forge would not open has nothing to label or attach.
    @staticmethod
    def test_a_part_the_forge_will_not_open_is_named(
        trial: Trial, project: Project
    ) -> None:
        trial.shell.replies(when="gh issue edit 1 --add-label edit --add-label epic")
        trial.shell.replies(
            when="gh api repos/{owner}/{repo}/issues -X POST*",
            exit_code=1,
            stderr="rate limited",
        )
        item = IdentifiedItem(
            number=1,
            kind="edit",
            epic=True,
            parts=[Part(title="first half", body="why", kind="feature", size="S")],
        )
        page = Page(identifying=Identifying(project=project), issues=[_issue(1)])

        transition = trial.walk(pin, Pinning(page=page, items=[item]))

        assert isinstance(transition, Leaf)
        assert transition.identified == [
            Identification(
                number=1,
                outcome="identified",
                item=item,
                refused=["could not open the issue: rate limited"],
            )
        ]
        assert trial.shell.commands[-1].startswith(
            "gh api repos/{owner}/{repo}/issues -X POST"
        )

    # A sub-issue the forge opened but would not attach points to nothing, so
    # its row carries its number beside the refusal.
    @staticmethod
    def test_a_sub_issue_opened_before_the_attach_fails_is_kept(
        trial: Trial, project: Project
    ) -> None:
        trial.shell.replies(when="gh issue edit 1 --add-label edit --add-label epic")
        trial.shell.replies(
            when="gh api repos/{owner}/{repo}/issues -X POST*",
            stdout='{"number": 10, "html_url": "https://github.com/o/r/issues/10"}',
        )
        trial.shell.replies(when=_labelled(10))
        trial.shell.replies(
            when="gh api repos/{owner}/{repo}/issues/10 --jq .id", stdout="99"
        )
        trial.shell.replies(
            when="gh api repos/{owner}/{repo}/issues/1/sub_issues*",
            exit_code=1,
            stderr="attach refused",
        )
        trial.shell.replies(
            when="gh api repos/{owner}/{repo}/issues/1/sub_issues --paginate*"
        )
        item = IdentifiedItem(
            number=1,
            kind="edit",
            epic=True,
            parts=[Part(title="first half", body="why", kind="feature", size="S")],
        )
        trial.shell.replies(when=_labelled(2))
        page = Page(
            identifying=Identifying(project=project), issues=[_issue(1), _issue(2)]
        )

        transition = trial.walk(pin, Pinning(page=page, items=[item, _item(2)]))

        assert isinstance(transition, Leaf)
        assert transition.identified == [
            Identification(
                number=1,
                outcome="identified",
                item=item,
                opened=[10],
                refused=["could not attach #10 under #1: attach refused"],
            ),
            *_identified(2),
        ]


class TestTally:
    # The cast hands back what it carried, under the carrier's own class
    # rather than the step's.
    @staticmethod
    def test_the_result_is_the_carrier(trial: Trial, project: Project) -> None:
        transition = trial.walk(
            tally, Tally(project=project, identified=_identified(1))
        )

        assert transition == Done(
            Identifying(project=project, identified=_identified(1))
        )


class TestCast:
    # Three issues, a page of two: two pages, one session, the skill read once.
    @staticmethod
    @pytest.mark.usefixtures("here")
    def test_pages_share_one_session_and_the_skill_is_named_once(trial: Trial) -> None:
        trial.shell.replies(
            when=_AUTHORED, stdout=json.dumps([_row(1), _row(2), _row(3)])
        )
        trial.shell.replies(when=_ASSIGNED, stdout="[]")
        trial.coding.replies(Identified(items=[_item(1), _item(2)]))
        trial.coding.replies(Identified(items=[_item(3)]))
        trial.shell.replies(when="gh issue edit*", always=True)

        result = trial.cast(identify, Identify(batch=2))

        assert result == Identifying(
            project=Project(), batch=2, briefed=True, identified=_identified(1, 2, 3)
        )
        assert trial.steps == [
            "gather",
            "leaf",
            "identify_page",
            "pin",
            "leaf",
            "identify_page",
            "pin",
            "leaf",
            "tally",
        ]
        first, second = trial.coding.prompts
        assert "SKILL.md" in first
        assert "SKILL.md" not in second
        assert trial.coding.calls[0].resume is None
        assert trial.coding.calls[1].resume == "s1"
        assert trial.deltas[-1].startswith("identify — 3 issues")

    @staticmethod
    @pytest.mark.usefixtures("here")
    def test_a_backlog_with_nothing_to_identify_asks_nothing(trial: Trial) -> None:
        trial.shell.replies(when=_AUTHORED, stdout=json.dumps([_row(1, "bug", "S")]))
        trial.shell.replies(when=_ASSIGNED, stdout="[]")

        result = trial.cast(identify, Identify())

        assert result == Identifying(project=Project())
        assert trial.steps == ["gather", "leaf", "tally"]
        assert trial.deltas == ["identify — 0 issues\n  (none wanted identifying)"]

    @staticmethod
    @pytest.mark.usefixtures("here")
    def test_a_stopped_cast_reports_then_fails(trial: Trial) -> None:
        trial.shell.replies(when=_AUTHORED, exit_code=1, stderr="not logged in")

        with pytest.raises(RitualError, match="not logged in"):
            trial.cast(identify, Identify())

        assert "the cast stopped" in trial.deltas[0]
