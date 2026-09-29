"""Refining your issues a page at a time, with one agent session for them all."""

import json

import pytest
from vekna.lexicon import Goto, RitualError
from vekna.trial import Trial

from cabinet.gates.ritual.vekna.refine import gather, leaf, refine_page, tally
from cabinet.pacts.issues import (
    Issue,
    Page,
    Refine,
    Refined,
    RefinedItem,
    Refinement,
    Refining,
)
from cabinet.pacts.project import Project
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

        transition = trial.walk(gather, Refining(project=project))

        assert isinstance(transition, Goto)
        assert transition.target is leaf
        assert isinstance(transition.payload, Refining)
        assert [one.number for one in transition.payload.queue] == [2, 3]

    @staticmethod
    def test_a_forge_that_will_not_list_stops_the_cast_with_the_report(
        trial: Trial, project: Project
    ) -> None:
        trial.shell.replies(when=_AUTHORED, exit_code=1, stderr="not logged in")

        transition = trial.walk(gather, Refining(project=project))

        assert isinstance(transition, Goto)
        assert transition.target is tally
        assert isinstance(transition.payload, Refining)
        assert "not logged in" in transition.payload.stopped


class TestLeaf:
    @staticmethod
    def test_a_declined_page_is_rowed_and_the_next_one_offered(
        trial: Trial, project: Project
    ) -> None:
        trial.decide.answers(answer=False, when="*refine these 2?")
        refining = Refining(
            project=project, batch=2, queue=[_issue(1), _issue(2), _issue(3)]
        )

        transition = trial.walk(leaf, refining)

        assert isinstance(transition, Goto)
        assert transition.target is leaf
        assert transition.payload == refining.but(
            queue=[_issue(3)],
            refined=[
                Refinement(number=1, outcome="declined"),
                Refinement(number=2, outcome="declined"),
            ],
        )


class TestRefinePage:
    @staticmethod
    def test_an_issue_the_agent_did_not_answer_for_is_named(
        trial: Trial, project: Project
    ) -> None:
        trial.coding.replies(Refined(items=[_item(1), _item(99)]))
        page = Page(refining=Refining(project=project), issues=[_issue(1), _issue(2)])

        transition = trial.walk(refine_page, page)

        assert isinstance(transition, Goto)
        assert transition.target is leaf
        assert transition.payload == Refining(
            project=project,
            briefed=True,
            refined=[*_refined(1), Refinement(number=2, outcome="missed")],
        )

    @staticmethod
    def test_the_refiner_reaches_issues_and_is_attended(
        trial: Trial, project: Project
    ) -> None:
        trial.coding.replies(Refined(items=[_item(1)]))

        trial.walk(
            refine_page, Page(refining=Refining(project=project), issues=[_issue(1)])
        )

        options = str(trial.coding.calls[0].focus_options)
        assert "Bash(gh issue:*)" in options
        assert "Edit" not in options
        assert "permission_mode='auto'" in options

    @staticmethod
    def test_an_answer_out_of_shape_stops_the_cast_with_the_page_rowed(
        trial: Trial, project: Project
    ) -> None:
        trial.coding.replies("no idea, sorry")
        page = Page(refining=Refining(project=project), issues=[_issue(1)])

        transition = trial.walk(refine_page, page)

        assert isinstance(transition, Goto)
        assert transition.target is tally
        assert isinstance(transition.payload, Refining)
        assert transition.payload.refined == [Refinement(number=1, outcome="stopped")]
        assert "shape" in transition.payload.stopped


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

        result = trial.cast(refine, Refine(batch=2))

        assert result == Refining(
            project=Project(), batch=2, briefed=True, refined=_refined(1, 2, 3)
        )
        assert trial.steps == [
            "gather",
            "leaf",
            "refine_page",
            "leaf",
            "refine_page",
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
