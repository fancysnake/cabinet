"""A payload rebuilt as the next step's class, and nothing more derived."""

from cabinet.pacts.project import Project
from cabinet.pacts.pulls import Closed, PullRequest, Run, Work
from cabinet.pacts.reviews import Branch, Picking, Read, Recap, Triage
from cabinet.pacts.sweep import CheckClean, NextPr, PushWork, SetAside

_PULL = PullRequest(
    number=7,
    title="pr 7",
    url="https://example.test/pull/7",
    branch="feature",
    base="main",
    updated_at="2026-08-01T22:00:00Z",
)


def _work() -> Work:
    return Work(run=Run(project=Project(), bound=3), pr=_PULL, note="n")


class TestTo:
    @staticmethod
    def test_a_sibling_is_rebuilt_with_every_field() -> None:
        pushing = _work().to(PushWork).charged("gate_check")

        aside = pushing.to(SetAside)

        assert aside.__class__ is SetAside
        assert aside.model_dump() == pushing.model_dump()

    # The engine routes by exact class, so the base is not the subclass it
    # was built from.
    @staticmethod
    def test_back_to_the_base_is_the_base() -> None:
        recap = Picking(project=Project(), bound=2).to(Recap)

        assert recap.to(Picking).__class__ is Picking


class TestHeld:
    @staticmethod
    def test_a_field_holds_its_own_class_whatever_it_was_handed() -> None:
        reading = Branch(
            picking=Picking(project=Project(), bound=2), name="feature", number=7
        ).to(Read)

        assert Triage(branch=reading, items=[]).branch.__class__ is Branch

    @staticmethod
    def test_a_closed_branch_is_equal_to_the_work_it_closed() -> None:
        work = _work()

        assert Closed(work=work.to(PushWork), outcome="green") == Closed(
            work=work, outcome="green"
        )

    @staticmethod
    def test_a_run_inside_work_is_a_run() -> None:
        queued = Run(project=Project(), bound=3).to(NextPr)

        assert CheckClean(run=queued, pr=_PULL).run.__class__ is Run
