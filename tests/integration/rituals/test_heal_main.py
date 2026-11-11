"""heal.main: a red base fixed on a branch of its own, and opened."""

import json

import pytest
from vekna.trial import Trial

from cabinet.gates.ritual.vekna.heal import muster_main, open_pull, push_work, tend
from cabinet.pacts.heal import (
    Chart,
    FinishPr,
    MusterMain,
    OpenPull,
    PickJob,
    PushWork,
    Tend,
)
from cabinet.pacts.healing import Heal, Run, Surveyed, Work
from cabinet.pacts.project import Project
from cabinet.pacts.pulls import Check, PullRequest
from cabinet.rituals.heal_main import heal_main
from tests.conftest import LIST, STATUS, board, listing, row

_RED = json.dumps(
    {
        "total_count": 2,
        "check_runs": [
            {"id": 1, "name": "checks", "conclusion": "failure"},
            {"id": 2, "name": "docs", "conclusion": "failure"},
        ],
    }
)
_GREEN = json.dumps({"total_count": 0, "check_runs": []})
_CHECKS = Check(name="checks", passed=False, id=1)
_BRANCH = "fix/main-abc1234"
_FETCH = "git fetch --prune origin"
_HEAD = "git rev-parse --short origin/main"
_CUT = f"git checkout --no-track -b {_BRANCH} origin/main || git checkout {_BRANCH}"
_BEYOND = "git rev-list --count origin/main..HEAD"
_OPEN = "gh api repos*pulls -X POST*"
_URL = "https://github.com/o/r/pull/9"
_OPENED = json.dumps({"number": 9, "html_url": _URL})
_SURVEYED = Surveyed(
    number=0, branch="main", url="", todos=["ci"], red=[_CHECKS], threads=0
)
_NOTHING = Surveyed(number=0, branch="main", url="", todos=[], red=[], threads=0)
_FIX = PullRequest(
    number=0,
    title="fix: make main green",
    url="",
    branch=_BRANCH,
    base="main",
    updated_at="",
)


def _pulls(trial: Trial, *rows: dict[str, object]) -> None:
    trial.shell.replies(
        when="git remote get-url origin", stdout="https://github.com/o/r.git\n"
    )
    trial.shell.replies(when="git config --get-urlmatch*", stdout="!gh auth\n")
    trial.shell.replies(when=LIST, stdout=listing(*rows))


def _listed(trial: Trial, *rows: dict[str, object], checks: str = _RED) -> None:
    _pulls(trial, *rows)
    trial.shell.replies(when=board("main"), stdout=checks)


def _run(project: Project) -> Run:
    return Run(project=project, attended=False, tasks=["ci"])


@pytest.fixture(name="fixing")
def _fixing(project: Project) -> Work:
    return Work(run=_run(project), pr=_FIX)


class TestMusterMain:
    @staticmethod
    def test_a_red_base_is_branched_and_handed_to_the_job_loop(
        trial: Trial, project: Project
    ) -> None:
        _listed(trial, row(7))
        trial.shell.replies(when=STATUS)
        trial.shell.replies(when=_FETCH)
        trial.shell.replies(when=_HEAD, stdout="abc1234\n")
        trial.shell.replies(when="git checkout --no-track*")
        run = _run(project)

        transition = trial.walk(muster_main, run.to(MusterMain))

        assert transition == Work(
            run=run.but(surveyed=[_SURVEYED]), pr=_FIX, red=[_CHECKS]
        ).to(PickJob)
        assert trial.shell.commands[-4:] == [STATUS, _FETCH, _HEAD, _CUT]
        assert trial.deltas == ["main: ci (checks)"]

    @staticmethod
    def test_a_fix_already_open_ends_the_cast(trial: Trial, project: Project) -> None:
        _listed(trial, row(8, headRefName="fix/main-0123abc"))
        run = _run(project)

        assert trial.walk(muster_main, run.to(MusterMain)) == run.to(Chart)
        assert trial.deltas == ["a fix for main is already open: #8 fix/main-0123abc"]
        assert trial.shell.commands[-1] == LIST

    @staticmethod
    def test_a_green_base_ends_the_cast(trial: Trial, project: Project) -> None:
        _listed(trial, checks=_GREEN)
        run = _run(project)

        assert trial.walk(muster_main, run.to(MusterMain)) == run.but(
            surveyed=[_NOTHING]
        ).to(Chart)
        assert trial.deltas == ["main: nothing to do"]

    @staticmethod
    def test_a_plan_says_what_is_red_and_cuts_no_branch(
        trial: Trial, project: Project
    ) -> None:
        _listed(trial)
        run = Run(project=project, tasks=[])

        assert trial.walk(muster_main, run.to(MusterMain)) == run.but(
            surveyed=[_SURVEYED]
        ).to(Chart)
        assert trial.shell.commands[-1] == board("main")

    @staticmethod
    def test_a_dirty_worktree_stops_the_cast(trial: Trial, project: Project) -> None:
        _listed(trial)
        trial.shell.replies(when=STATUS, stdout=" M src/thing.py\n")
        run = _run(project)

        assert trial.walk(muster_main, run.to(MusterMain)) == run.but(
            surveyed=[_SURVEYED], stopped="the worktree is not clean:\nM src/thing.py"
        ).to(Chart)

    @staticmethod
    def test_a_board_the_forge_will_not_read_stops_the_cast(
        trial: Trial, project: Project
    ) -> None:
        _pulls(trial)
        trial.shell.replies(when=board("main"), exit_code=1, stderr="not logged in")
        run = _run(project)

        assert trial.walk(muster_main, run.to(MusterMain)) == run.but(
            stopped="gh could not read the check board: not logged in"
        ).to(Chart)

    @staticmethod
    @pytest.mark.usefixtures("here")
    def test_a_plan_is_a_whole_cast(trial: Trial) -> None:
        _listed(trial)

        result = trial.cast(heal_main, Heal(plan_only=True))

        assert result.surveyed == [_SURVEYED]
        assert trial.steps == ["muster_main", "chart"]


class TestTend:
    @staticmethod
    def test_a_branch_with_no_pull_request_goes_to_have_one_opened(
        trial: Trial, fixing: Work
    ) -> None:
        assert trial.walk(tend, fixing.to(Tend)) == fixing.to(OpenPull)


class TestPushWork:
    # A fix that stood down with nothing committed: pushed, the branch would
    # be a copy of the base on the remote, with no pull request to it.
    @staticmethod
    def test_a_branch_with_no_commit_past_the_base_is_not_pushed(
        trial: Trial, fixing: Work
    ) -> None:
        trial.shell.replies(when=_BEYOND, stdout="0\n")
        stood_down = fixing.standing_down("")

        assert trial.walk(push_work, stood_down.to(PushWork)) == fixing.to(Tend)
        assert trial.shell.commands == [_BEYOND]

    @staticmethod
    def test_a_fix_that_was_committed_is_pushed(trial: Trial, fixing: Work) -> None:
        trial.shell.replies(when=_BEYOND, stdout="1\n")
        trial.shell.replies(when=f"git push origin {_BRANCH}")

        assert trial.walk(push_work, fixing.landed().to(PushWork)) == fixing.to(Tend)
        assert trial.shell.commands == [_BEYOND, f"git push origin {_BRANCH}"]


class TestOpenPull:
    @staticmethod
    def test_the_row_takes_the_number_the_forge_gave(
        trial: Trial, fixing: Work
    ) -> None:
        trial.shell.replies(when=_BEYOND, stdout="1\n")
        trial.shell.replies(when=_OPEN, stdout=_OPENED)

        assert trial.walk(open_pull, fixing.to(OpenPull)) == fixing.opened(
            9, _URL
        ).noting(_URL).to(FinishPr)
        assert trial.shell.commands[-1] == (
            "gh api repos/{owner}/{repo}/pulls -X POST"
            f" -f head={_BRANCH} -f base=main"
            " -f title='fix: make main green'"
            " -f body='`heal.main` found `main` red and fixed it on this branch.'"
        )

    @staticmethod
    def test_a_blocked_branch_is_opened_saying_what_stopped_it(
        trial: Trial, fixing: Work
    ) -> None:
        trial.shell.replies(when=_BEYOND, stdout="1\n")
        trial.shell.replies(when=_OPEN, stdout=_OPENED)
        blocked = fixing.stopped_by("the gate is still red")

        transition = trial.walk(open_pull, blocked.to(OpenPull))

        assert isinstance(transition, FinishPr)
        assert transition.pr.url == _URL
        assert "the gate is still red" in trial.shell.commands[-1]

    @staticmethod
    def test_nothing_committed_is_nothing_opened(trial: Trial, fixing: Work) -> None:
        trial.shell.replies(when=_BEYOND, stdout="0\n")

        assert trial.walk(open_pull, fixing.to(OpenPull)) == fixing.noting(
            "nothing was committed, so no pull request was opened"
        ).to(FinishPr)
        assert trial.shell.commands == [_BEYOND]

    @staticmethod
    def test_a_forge_that_refuses_is_noted(trial: Trial, fixing: Work) -> None:
        trial.shell.replies(when=_BEYOND, stdout="1\n")
        trial.shell.replies(when=_OPEN, exit_code=1, stderr="no such head")

        assert trial.walk(open_pull, fixing.to(OpenPull)) == fixing.noting(
            "could not open the pull request: no such head"
        ).to(FinishPr)
