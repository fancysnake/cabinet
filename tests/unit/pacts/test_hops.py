"""A payload rebuilt as the next step's class, and nothing more derived."""

from cabinet.pacts.heal import Chart, CheckClean, PushWork, SetAside, Survey
from cabinet.pacts.healing import Run, Work
from cabinet.pacts.project import Project
from cabinet.pacts.pulls import PullRequest

_PULL = PullRequest(
    number=7,
    title="pr 7",
    url="https://example.test/pull/7",
    branch="feature",
    base="main",
    updated_at="2026-08-01T22:00:00Z",
)


def _work() -> Work:
    return Work(run=Run(project=Project()), pr=_PULL, note="n")


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
        chart = Run(project=Project()).to(Chart)

        assert chart.to(Run).__class__ is Run


class TestHeld:
    @staticmethod
    def test_a_run_inside_work_is_a_run() -> None:
        queued = Run(project=Project()).to(Survey)

        assert CheckClean(run=queued, pr=_PULL).run.__class__ is Run

    @staticmethod
    def test_a_branch_ended_is_equal_to_the_work_it_ended() -> None:
        work = _work()

        assert work.to(PushWork).to(Work) == work
