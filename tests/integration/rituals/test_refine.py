"""Refining your issues a page at a time, with one agent session for them all."""

import json

import pytest
from vekna.lexicon import Done, RitualError
from vekna.trial import Trial

from cabinet.gates.ritual.vekna.refine import gather, leaf, pin, refine_page, tally
from cabinet.pacts.issues import (
    Issue,
    Page,
    Part,
    Pinning,
    Refine,
    Refined,
    RefinedItem,
    Refinement,
    Refining,
)
from cabinet.pacts.project import Project
from cabinet.pacts.refine import Gather, Leaf, Tally
from cabinet.rituals.refine import refine

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


def _item(number: int) -> RefinedItem:
    return RefinedItem(number=number, kind="feature", size="S")


def _labelled(number: int) -> str:
    return f"gh issue edit {number} --add-label feature --add-label S"


def _refined(*numbers: int) -> list[Refinement]:
    return [
        Refinement(number=number, outcome="refined", item=_item(number))
        for number in numbers
    ]


class TestGather:
    @staticmethod
    def test_only_the_unrefined_are_queued(trial: Trial, project: Project) -> None:
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
    def test_a_declined_page_is_rowed_and_the_next_one_offered(
        trial: Trial, project: Project
    ) -> None:
        trial.decide.answers(answer=False, when="*refine these 2?")
        refining = Leaf(
            project=project, batch=2, queue=[_issue(1), _issue(2), _issue(3)]
        )

        transition = trial.walk(leaf, refining)

        assert transition == refining.but(
            queue=[_issue(3)],
            refined=[
                Refinement(number=1, outcome="declined"),
                Refinement(number=2, outcome="declined"),
            ],
        )


class TestRefinePage:
    @staticmethod
    def test_the_reading_goes_to_the_forge_writes(
        trial: Trial, project: Project
    ) -> None:
        trial.coding.replies(Refined(items=[_item(1)]))
        page = Page(refining=Refining(project=project), issues=[_issue(1)])

        transition = trial.walk(refine_page, page)

        assert transition == Pinning(page=page, items=[_item(1)])

    # An issue the agent invented is not on the page, so nothing is put on it.
    @staticmethod
    def test_an_issue_that_was_never_on_the_page_is_dropped(
        trial: Trial, project: Project
    ) -> None:
        trial.coding.replies(Refined(items=[_item(1), _item(99)]))
        page = Page(refining=Refining(project=project), issues=[_issue(1)])

        transition = trial.walk(refine_page, page)

        assert isinstance(transition, Pinning)
        assert transition.items == [_item(1)]

    @staticmethod
    def test_the_agent_only_reads_and_reaches_no_forge(
        trial: Trial, project: Project
    ) -> None:
        trial.coding.replies(Refined(items=[_item(1)]))

        trial.walk(
            refine_page, Page(refining=Refining(project=project), issues=[_issue(1)])
        )

        allowed = trial.coding.calls[0].focus_options.allowed_tools
        options = str(trial.coding.calls[0].focus_options)
        assert not [one for one in allowed if "gh " in one or "glab " in one]
        assert "Edit" not in allowed
        assert "permission_mode='dontAsk'" in options
        assert not trial.shell.commands

    @staticmethod
    def test_an_answer_out_of_shape_stops_the_cast_with_the_page_rowed(
        trial: Trial, project: Project
    ) -> None:
        trial.coding.replies("no idea, sorry")
        page = Page(refining=Refining(project=project), issues=[_issue(1)])

        transition = trial.walk(refine_page, page)

        assert isinstance(transition, Tally)
        assert transition.refined == [Refinement(number=1, outcome="stopped")]
        assert "shape" in transition.stopped


class TestPin:
    @staticmethod
    def test_the_labels_go_on_and_the_page_is_rowed(
        trial: Trial, project: Project
    ) -> None:
        trial.shell.replies(when=_labelled(1))
        page = Page(refining=Refining(project=project), issues=[_issue(1)])

        transition = trial.walk(pin, Pinning(page=page, items=[_item(1)]))

        assert transition == Leaf(project=project, briefed=True, refined=_refined(1))
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
        trial.shell.replies(when="gh api repos/{owner}/{repo}/issues/1/sub_issues*")
        item = RefinedItem(
            number=1,
            kind="edit",
            epic=True,
            parts=[Part(title="first half", body="why", kind="feature", size="S")],
        )
        page = Page(refining=Refining(project=project), issues=[_issue(1)])

        transition = trial.walk(pin, Pinning(page=page, items=[item]))

        assert isinstance(transition, Leaf)
        assert transition.refined == [
            Refinement(number=1, outcome="refined", item=item, opened=[10])
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
        trial.shell.replies(when="gh api repos*sub_issues*")
        trial.shell.replies(when="gh api repos*blocked_by*")
        item = RefinedItem(
            number=1, kind="feature", size="S", children=[8], blocked_by=[9]
        )
        page = Page(refining=Refining(project=project), issues=[_issue(1)])

        transition = trial.walk(pin, Pinning(page=page, items=[item]))

        assert isinstance(transition, Leaf)
        assert trial.shell.commands[2].endswith("sub_issues -X POST -F sub_issue_id=99")
        assert trial.shell.commands[4].endswith("blocked_by -X POST -F issue_id=99")

    @staticmethod
    def test_an_issue_the_agent_did_not_answer_for_is_named(
        trial: Trial, project: Project
    ) -> None:
        trial.shell.replies(when=_labelled(1))
        page = Page(refining=Refining(project=project), issues=[_issue(1), _issue(2)])

        transition = trial.walk(pin, Pinning(page=page, items=[_item(1)]))

        assert transition == Leaf(
            project=project,
            briefed=True,
            refined=[*_refined(1), Refinement(number=2, outcome="missed")],
        )

    # What is already on stays on: the issue in flight and everything behind
    # it are named as half done, and the cast ends rather than labelling on.
    @staticmethod
    def test_a_forge_that_refuses_mid_page_stops_the_cast(
        trial: Trial, project: Project
    ) -> None:
        trial.shell.replies(when=_labelled(1))
        trial.shell.replies(when=_labelled(2), exit_code=1, stderr="no such label")
        page = Page(
            refining=Refining(project=project), issues=[_issue(1), _issue(2), _issue(3)]
        )

        transition = trial.walk(
            pin, Pinning(page=page, items=[_item(1), _item(2), _item(3)])
        )

        assert isinstance(transition, Tally)
        assert transition.refined == [
            *_refined(1),
            Refinement(number=2, outcome="stopped"),
            Refinement(number=3, outcome="stopped"),
        ]
        assert "no such label" in transition.stopped

    # A sub-issue the forge opened but would not attach points to nothing, so
    # the row the cast stopped on carries its number.
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
        item = RefinedItem(
            number=1,
            kind="edit",
            epic=True,
            parts=[Part(title="first half", body="why", kind="feature", size="S")],
        )
        page = Page(refining=Refining(project=project), issues=[_issue(1), _issue(2)])

        transition = trial.walk(pin, Pinning(page=page, items=[item, _item(2)]))

        assert isinstance(transition, Tally)
        assert transition.refined == [
            Refinement(number=1, outcome="stopped", opened=[10]),
            Refinement(number=2, outcome="stopped"),
        ]
        assert "attach refused" in transition.stopped


class TestTally:
    # The cast hands back what it carried, under the carrier's own class
    # rather than the step's.
    @staticmethod
    def test_the_result_is_the_carrier(trial: Trial, project: Project) -> None:
        transition = trial.walk(tally, Tally(project=project, refined=_refined(1)))

        assert transition == Done(Refining(project=project, refined=_refined(1)))


class TestCast:
    # Three issues, a page of two: two pages, one session, the skill read once.
    @staticmethod
    @pytest.mark.usefixtures("here")
    def test_pages_share_one_session_and_the_skill_is_named_once(trial: Trial) -> None:
        trial.shell.replies(
            when=_AUTHORED, stdout=json.dumps([_row(1), _row(2), _row(3)])
        )
        trial.shell.replies(when=_ASSIGNED, stdout="[]")
        trial.decide.answers(answer=True, when="*refine these *", always=True)
        trial.coding.replies(Refined(items=[_item(1), _item(2)]))
        trial.coding.replies(Refined(items=[_item(3)]))
        trial.shell.replies(when="gh issue edit*", always=True)

        result = trial.cast(refine, Refine(batch=2))

        assert result == Refining(
            project=Project(), batch=2, briefed=True, refined=_refined(1, 2, 3)
        )
        assert trial.steps == [
            "gather",
            "leaf",
            "refine_page",
            "pin",
            "leaf",
            "refine_page",
            "pin",
            "leaf",
            "tally",
        ]
        first, second = trial.coding.prompts
        assert "SKILL.md" in first
        assert "SKILL.md" not in second
        assert trial.coding.calls[0].resume is None
        assert trial.coding.calls[1].resume == "s1"
        assert trial.deltas[-1].startswith("refine — 3 issues")

    @staticmethod
    @pytest.mark.usefixtures("here")
    def test_a_backlog_with_nothing_to_refine_asks_nothing(trial: Trial) -> None:
        trial.shell.replies(when=_AUTHORED, stdout=json.dumps([_row(1, "bug", "S")]))
        trial.shell.replies(when=_ASSIGNED, stdout="[]")

        result = trial.cast(refine, Refine())

        assert result == Refining(project=Project())
        assert trial.steps == ["gather", "leaf", "tally"]
        assert trial.deltas == ["refine — 0 issues\n  (none wanted refining)"]

    @staticmethod
    @pytest.mark.usefixtures("here")
    def test_a_stopped_cast_reports_then_fails(trial: Trial) -> None:
        trial.shell.replies(when=_AUTHORED, exit_code=1, stderr="not logged in")

        with pytest.raises(RitualError, match="not logged in"):
            trial.cast(refine, Refine())

        assert "the cast stopped" in trial.deltas[0]
