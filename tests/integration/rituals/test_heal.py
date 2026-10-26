"""Mustering pull requests, surveying them into todo lists, and planning."""

import json

import pytest
from pydantic import BaseModel
from typing_extensions import override
from vekna.lexicon import CAST_QUEUE, CastEnded, CastQueueProtocol, NoDaemonError
from vekna.trial import Trial

from cabinet.gates.ritual.vekna.heal import (
    muster_mine,
    muster_pr,
    muster_this,
    summon,
    survey,
)
from cabinet.pacts.heal import (
    Chart,
    CheckClean,
    MusterMine,
    MusterPr,
    MusterThis,
    Summon,
    Survey,
)
from cabinet.pacts.healing import (
    Heal,
    Healed,
    HealPr,
    Queued,
    Run,
    Surveyed,
    Unsurveyed,
)
from cabinet.pacts.project import Project
from cabinet.pacts.pulls import Check, PullRequest
from cabinet.pacts.services import services
from cabinet.rituals.heal_mine import heal_mine
from cabinet.rituals.heal_this import heal_this
from cabinet.specs import HEAL_STEPS
from tests.conftest import (
    HERE,
    LIST,
    THREADS,
    board,
    comment,
    listing,
    node,
    page,
    row,
    threads_page,
)

_URL = "https://github.com/o/r/pull/7"
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
_OPEN = threads_page(page([node("PRRT_1", page([comment(101)]))]))
_NONE = threads_page(page([]))
_MERGE_TREE = "git merge-tree --write-tree origin/main origin/feature > /dev/null"
# The preflight's two, the listing, the board and the threads.
_READS = 5


# What a cast meets with no daemon listening, as vekna's own CLI binds it.
class _Daemonless(CastQueueProtocol):
    @override
    async def enqueue(self, *, ritual: str, components: BaseModel) -> str:
        raise NoDaemonError(ritual)

    @override
    async def await_end(self, cast_id: str) -> CastEnded:
        raise NoDaemonError(cast_id)


def _preflight(trial: Trial) -> None:
    trial.shell.replies(
        when="git remote get-url origin", stdout="https://github.com/o/r.git\n"
    )
    trial.shell.replies(when="git config --get-urlmatch*", stdout="!gh auth\n")


def _surveying(pull: PullRequest, project: Project) -> Survey:
    return Survey(project=project, queue=[pull])


def _planning(pull: PullRequest, project: Project) -> Survey:
    return Survey(project=project, tasks=[], queue=[pull])


def _labelled(*names: str) -> list[dict[str, str]]:
    return [{"name": name} for name in names]


class TestMuster:
    @staticmethod
    def test_mine_queues_what_is_wanted_oldest_first(
        trial: Trial, project: Project
    ) -> None:
        _preflight(trial)
        trial.shell.replies(
            when=LIST,
            stdout=listing(
                row(8, updatedAt="2026-08-02T00:00:00Z"),
                row(9, labels=_labelled("pr::wait")),
                row(7),
            ),
        )

        transition = trial.walk(muster_mine, MusterMine(project=project))

        assert isinstance(transition, Survey)
        assert [pull.number for pull in transition.queue] == [7, 8]
        assert transition.reserved == services().steps.opening(2)

    @staticmethod
    def test_this_takes_the_branch_at_the_cwd(trial: Trial, project: Project) -> None:
        _preflight(trial)
        trial.shell.replies(when=LIST, stdout=listing(row(8), row(7)))
        trial.shell.replies(when=HERE, stdout="feature\n")

        transition = trial.walk(muster_this, MusterThis(project=project))

        assert isinstance(transition, Survey)
        assert [pull.number for pull in transition.queue] == [7]

    @staticmethod
    def test_this_without_a_pull_request_goes_to_the_report(
        trial: Trial, project: Project
    ) -> None:
        _preflight(trial)
        trial.shell.replies(when=LIST, stdout=listing(row(8)))
        trial.shell.replies(when=HERE, stdout="feature\n")

        assert trial.walk(muster_this, MusterThis(project=project)) == Run(
            project=project,
            stopped="no open pull request of yours has feature as its branch",
        ).to(Chart)

    # Wherever the cwd stands, and wait label or not: it was asked for by
    # number.
    @staticmethod
    def test_pr_takes_the_one_it_was_queued_for(trial: Trial, project: Project) -> None:
        _preflight(trial)
        trial.shell.replies(
            when=LIST, stdout=listing(row(8), row(7, labels=_labelled("pr::wait")))
        )

        transition = trial.walk(muster_pr, MusterPr(run=Run(project=project), number=7))

        assert isinstance(transition, Survey)
        assert [pull.number for pull in transition.queue] == [7]
        assert transition.reserved == services().steps.opening(1)

    @staticmethod
    def test_pr_that_is_no_longer_open_goes_to_the_report(
        trial: Trial, project: Project
    ) -> None:
        _preflight(trial)
        trial.shell.replies(when=LIST, stdout=listing(row(8)))

        assert trial.walk(
            muster_pr, MusterPr(run=Run(project=project), number=7)
        ) == Run(project=project, stopped="no open pull request of yours is #7").to(
            Chart
        )

    @staticmethod
    def test_pr_with_a_forge_that_will_not_list_goes_to_the_report(
        trial: Trial, project: Project
    ) -> None:
        _preflight(trial)
        trial.shell.replies(when=LIST, exit_code=1, stderr="not logged in")

        transition = trial.walk(muster_pr, MusterPr(run=Run(project=project), number=7))

        assert isinstance(transition, Chart)
        assert transition.stopped.endswith("not logged in")

    @staticmethod
    def test_a_forge_that_will_not_list_goes_to_the_report(
        trial: Trial, project: Project
    ) -> None:
        _preflight(trial)
        trial.shell.replies(when=LIST, exit_code=1, stderr="not logged in")

        assert trial.walk(muster_mine, MusterMine(project=project)) == Run(
            project=project,
            stopped="gh could not list your pull requests: not logged in",
        ).to(Chart)

    @staticmethod
    def test_an_ssh_remote_stops_before_anything_is_fetched(
        trial: Trial, project: Project
    ) -> None:
        trial.shell.replies(
            when="git remote get-url origin", stdout="git@github.com:o/r.git\n"
        )

        transition = trial.walk(muster_this, MusterThis(project=project))

        assert isinstance(transition, Chart)
        assert "not https" in transition.stopped
        assert LIST not in trial.shell.commands


class TestSurvey:
    @staticmethod
    def test_an_empty_queue_is_charted(trial: Trial, project: Project) -> None:
        run = Survey(project=project)

        assert trial.walk(survey, run) == run.to(Chart)

    @staticmethod
    def test_the_facts_become_todos_and_a_line(
        trial: Trial, pull: PullRequest, project: Project
    ) -> None:
        trial.shell.replies(when=board(), stdout=_RED)
        trial.shell.replies(when=THREADS, stdout=_OPEN)
        conflicted = pull.model_copy(update={"conflicted": True})

        transition = trial.walk(survey, _planning(conflicted, project))

        assert isinstance(transition, Survey)
        assert transition.queue == []
        assert transition.surveyed == [
            Surveyed(
                number=7,
                branch="feature",
                url=_URL,
                todos=["merge", "ci", "answer", "review"],
                red=[_CHECKS],
                threads=1,
            )
        ]
        assert trial.deltas == [
            "#7 feature: merge, ci (checks), answer (1 thread), review"
        ]

    @staticmethod
    def test_git_settles_what_the_forge_has_not_worked_out(
        trial: Trial, pull: PullRequest, project: Project
    ) -> None:
        trial.shell.replies(when=board(), stdout=_GREEN)
        trial.shell.replies(when=THREADS, stdout=_NONE)
        trial.shell.replies(when="git fetch origin main feature")
        trial.shell.replies(when=_MERGE_TREE, exit_code=1)
        reviewed = pull.model_copy(update={"labels": ["pr::thermo", "v:guide:done"]})

        transition = trial.walk(survey, _planning(reviewed, project))

        assert isinstance(transition, Survey)
        assert transition.surveyed[0].todos == ["merge"]

    @staticmethod
    def test_a_branch_with_nothing_left_is_guided(
        trial: Trial, pull: PullRequest, project: Project
    ) -> None:
        trial.shell.replies(when=board(), stdout=_GREEN)
        trial.shell.replies(when=THREADS, stdout=_NONE)
        clean = pull.model_copy(update={"conflicted": False, "labels": ["pr::thermo"]})

        transition = trial.walk(survey, _planning(clean, project))

        assert isinstance(transition, Survey)
        assert transition.surveyed[0].todos == ["guide"]
        assert trial.deltas == ["#7 feature: guide"]

    @staticmethod
    def test_a_branch_the_forge_will_not_answer_about_is_a_row(
        trial: Trial, pull: PullRequest, project: Project
    ) -> None:
        trial.shell.replies(when=board(), exit_code=1, stderr="rate limited")

        transition = trial.walk(survey, _surveying(pull, project))

        assert isinstance(transition, Survey)
        assert isinstance(unread := transition.surveyed[0], Unsurveyed)
        assert "rate limited" in unread.note
        assert trial.deltas[0].startswith("#7 feature: could not survey:")

    # Taken with what this cast works and nothing else, the worst it can
    # spend spoken for.
    @staticmethod
    def test_a_branch_with_work_is_taken(
        trial: Trial, pull: PullRequest, project: Project
    ) -> None:
        trial.shell.replies(when=board(), stdout=_RED)
        trial.shell.replies(when=THREADS, stdout=_OPEN)
        conflicted = pull.model_copy(update={"conflicted": True})
        run = _surveying(conflicted, project)
        share = services().steps.heal_share(run)
        assert share is not None

        transition = trial.walk(survey, run)

        assert isinstance(transition, CheckClean)
        assert transition.todos == ["merge", "ci", "review"]
        assert transition.red == [_CHECKS]
        assert transition.run.reserved == share
        assert transition.run.queue == []

    # Every item of a triage is the operator's to decide, so only a cast with
    # somebody at the terminal answers threads.
    @staticmethod
    def test_an_attended_cast_takes_the_threads_too(
        trial: Trial, pull: PullRequest, project: Project
    ) -> None:
        trial.shell.replies(when=board(), stdout=_GREEN)
        trial.shell.replies(when=THREADS, stdout=_OPEN)
        clean = pull.model_copy(update={"conflicted": False})
        run = Survey(project=project, attended=True, queue=[clean])

        transition = trial.walk(survey, run)

        assert isinstance(transition, CheckClean)
        assert transition.todos == ["answer", "review"]

    @staticmethod
    def test_a_task_ritual_takes_only_its_task(
        trial: Trial, pull: PullRequest, project: Project
    ) -> None:
        trial.shell.replies(when=board(), stdout=_GREEN)
        trial.shell.replies(when=THREADS, stdout=_NONE)
        conflicted = pull.model_copy(update={"conflicted": True})
        run = Survey(project=project, tasks=["review"], queue=[conflicted])

        transition = trial.walk(survey, run)

        assert isinstance(transition, CheckClean)
        assert transition.todos == ["review"]

    @staticmethod
    def test_a_branch_with_nothing_this_cast_works_is_not_taken(
        trial: Trial, pull: PullRequest, project: Project
    ) -> None:
        trial.shell.replies(when=board(), stdout=_GREEN)
        trial.shell.replies(when=THREADS, stdout=_NONE)
        clean = pull.model_copy(update={"conflicted": False})
        run = Survey(project=project, tasks=["merge"], queue=[clean])

        transition = trial.walk(survey, run)

        assert isinstance(transition, Survey)
        assert transition.surveyed[0].todos == ["review"]

    # Nothing is spoken for: the branch's steps are its own cast's to spend.
    @staticmethod
    def test_a_fanning_cast_summons_a_branch_with_work(
        trial: Trial, pull: PullRequest, project: Project
    ) -> None:
        trial.shell.replies(when=board(), stdout=_RED)
        trial.shell.replies(when=THREADS, stdout=_NONE)
        conflicted = pull.model_copy(update={"conflicted": True})
        run = Survey(project=project, fan_out=True, queue=[conflicted])

        transition = trial.walk(survey, run)

        assert isinstance(transition, Summon)
        assert transition.pull == conflicted
        assert transition.run.queue == []
        assert transition.run.reserved == 0

    # Nothing went wrong, so nothing fails: the branch stays on the queue,
    # unread, for the report to name.
    @staticmethod
    def test_a_branch_the_budget_has_no_room_for_ends_the_cast(
        trial: Trial, pull: PullRequest, project: Project
    ) -> None:
        full = Survey(project=project, queue=[pull], reserved=HEAL_STEPS)

        assert trial.walk(survey, full) == full.to(Chart)
        assert not trial.shell.commands


class TestSummon:
    @staticmethod
    def test_the_branch_is_queued_as_a_cast_of_its_own(
        trial: Trial, pull: PullRequest, project: Project
    ) -> None:
        run = Run(project=project, bound=2, attended=True, batch=4)

        transition = trial.walk(summon, Summon(run=run, pull=pull))

        assert transition == run.summoned(
            Queued(number=7, branch="feature", cast="c1")
        ).to(Survey)
        [queued] = trial.queue.enqueued
        assert queued.ritual == "heal.pr"
        assert queued.components == HealPr(number=7, bound=2, attended=True, batch=4)

    @staticmethod
    def test_with_no_daemon_the_cast_fails_after_its_report(
        trial: Trial, pull: PullRequest, project: Project
    ) -> None:
        run = Run(project=project)

        with CAST_QUEUE.scope(_Daemonless()):
            transition = trial.walk(summon, Summon(run=run, pull=pull))

        assert isinstance(transition, Chart)
        assert transition.stopped.endswith("start it with `vekna`")
        assert transition.queued == []


class TestWholeCast:
    # Each branch with work goes to a cast of its own; the one with nothing
    # to do is said and left.
    @staticmethod
    @pytest.mark.usefixtures("here")
    def test_mine_queues_a_cast_per_branch_with_work(trial: Trial) -> None:
        _preflight(trial)
        trial.shell.replies(
            when=LIST,
            stdout=listing(
                row(mergeable="CONFLICTING"),
                row(8, mergeable="MERGEABLE", labels=_labelled("pr::thermo")),
            ),
        )
        for name in ("feature", "feature-8"):
            trial.shell.replies(when=board(name), stdout=_GREEN)
        trial.shell.replies(when=THREADS, stdout=_NONE)
        trial.shell.replies(when="slug=*gh api graphql*-F number=8", stdout=_NONE)

        result = trial.cast(heal_mine, Heal(bound=2))

        assert result.queued == [Queued(number=7, branch="feature", cast="c1")]
        assert [one.components for one in trial.queue.enqueued] == [
            HealPr(number=7, bound=2)
        ]
        assert trial.steps == [
            "muster_mine",
            "survey",
            "summon",
            "survey",
            "survey",
            "chart",
        ]
        assert trial.deltas[-1] == "heal — 1 queued\n\n  #7 feature: cast c1\n"

    @staticmethod
    @pytest.mark.usefixtures("here")
    def test_a_plan_surveys_and_writes_nothing(trial: Trial) -> None:
        _preflight(trial)
        trial.shell.replies(
            when=LIST, stdout=listing(row(mergeable="CONFLICTING", labels=[]))
        )
        trial.shell.replies(when=board(), stdout=_GREEN)
        trial.shell.replies(when=THREADS, stdout=_NONE)

        result = trial.cast(heal_mine, Heal(plan_only=True))

        assert result == Healed(
            surveyed=[
                Surveyed(
                    number=7,
                    branch="feature",
                    url=_URL,
                    todos=["merge", "review"],
                    red=[],
                    threads=0,
                )
            ]
        )
        assert trial.steps == ["muster_mine", "survey", "survey", "chart"]
        # Every other command, a write among them, would have found nothing
        # scripted to answer it.
        assert len(trial.shell.commands) == _READS
        assert trial.queue.enqueued == []

    @staticmethod
    @pytest.mark.usefixtures("here")
    def test_this_plans_the_branch_at_the_cwd(trial: Trial) -> None:
        _preflight(trial)
        trial.shell.replies(
            when=LIST, stdout=listing(row(8), row(mergeable="MERGEABLE"))
        )
        trial.shell.replies(when=HERE, stdout="feature\n")
        trial.shell.replies(when=board(), stdout=_GREEN)
        trial.shell.replies(when=THREADS, stdout=_NONE)

        result = trial.cast(heal_this, Heal(plan_only=True))

        assert [one.number for one in result.surveyed] == [7]
        assert trial.steps == ["muster_this", "survey", "survey", "chart"]
        assert trial.deltas == ["#7 feature: review"]
