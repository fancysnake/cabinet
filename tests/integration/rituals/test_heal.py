"""Surveying pull requests into todo lists, and changing nothing."""

import json

import pytest
from vekna.lexicon import Done, RitualError
from vekna.trial import Trial

from cabinet.gates.ritual.vekna.heal import chart, muster_mine, muster_this, survey
from cabinet.pacts.forge import ForgeError
from cabinet.pacts.heal import Chart, MusterMine, MusterThis, Survey
from cabinet.pacts.healing import Heal, Plan, Surveyed, Unsurveyed
from cabinet.pacts.project import Project
from cabinet.pacts.pulls import PullRequest
from cabinet.rituals.heal_mine import heal_mine
from cabinet.rituals.heal_this import heal_this
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
            {"name": "checks", "conclusion": "failure"},
            {"name": "docs", "conclusion": "failure"},
        ],
    }
)
_GREEN = json.dumps({"total_count": 0, "check_runs": []})
_OPEN = threads_page(page([node("PRRT_1", page([comment(101)]))]))
_NONE = threads_page(page([]))
_MERGE_TREE = "git merge-tree --write-tree origin/main origin/feature > /dev/null"
# The listing, the board and the threads.
_READS = 3


def _surveying(pull: PullRequest, project: Project) -> Survey:
    return Survey(project=project, queue=[pull])


def _labelled(*names: str) -> list[dict[str, str]]:
    return [{"name": name} for name in names]


class TestMuster:
    @staticmethod
    def test_mine_queues_what_is_wanted_oldest_first(
        trial: Trial, project: Project
    ) -> None:
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

    @staticmethod
    def test_this_takes_the_branch_at_the_cwd(trial: Trial, project: Project) -> None:
        trial.shell.replies(when=LIST, stdout=listing(row(8), row(7)))
        trial.shell.replies(when=HERE, stdout="feature\n")

        transition = trial.walk(muster_this, MusterThis(project=project))

        assert isinstance(transition, Survey)
        assert [pull.number for pull in transition.queue] == [7]

    @staticmethod
    def test_this_without_a_pull_request_ends_the_cast(
        trial: Trial, project: Project
    ) -> None:
        trial.shell.replies(when=LIST, stdout=listing(row(8)))
        trial.shell.replies(when=HERE, stdout="feature\n")

        with pytest.raises(RitualError, match="has feature as its branch"):
            trial.walk(muster_this, MusterThis(project=project))

    @staticmethod
    def test_a_forge_that_will_not_list_ends_the_cast(
        trial: Trial, project: Project
    ) -> None:
        trial.shell.replies(when=LIST, exit_code=1, stderr="not logged in")

        with pytest.raises(ForgeError, match="not logged in"):
            trial.walk(muster_mine, MusterMine(project=project))


class TestSurvey:
    @staticmethod
    def test_an_empty_queue_is_charted(trial: Trial, project: Project) -> None:
        healing = Survey(project=project)

        assert trial.walk(survey, healing) == healing.to(Chart)

    @staticmethod
    def test_the_facts_become_todos_and_a_line(
        trial: Trial, pull: PullRequest, project: Project
    ) -> None:
        trial.shell.replies(when=board(), stdout=_RED)
        trial.shell.replies(when=THREADS, stdout=_OPEN)
        conflicted = pull.model_copy(update={"conflicted": True})

        transition = trial.walk(survey, _surveying(conflicted, project))

        assert isinstance(transition, Survey)
        assert transition.queue == []
        assert transition.surveyed == [
            Surveyed(
                number=7,
                branch="feature",
                url=_URL,
                todos=["merge", "ci", "answer", "review"],
                red=["checks"],
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

        transition = trial.walk(survey, _surveying(reviewed, project))

        assert isinstance(transition, Survey)
        assert transition.surveyed[0].todos == ["merge"]

    @staticmethod
    def test_a_branch_with_nothing_left_is_guided(
        trial: Trial, pull: PullRequest, project: Project
    ) -> None:
        trial.shell.replies(when=board(), stdout=_GREEN)
        trial.shell.replies(when=THREADS, stdout=_NONE)
        clean = pull.model_copy(update={"conflicted": False, "labels": ["pr::thermo"]})

        transition = trial.walk(survey, _surveying(clean, project))

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


class TestChart:
    @staticmethod
    def test_the_plan_is_every_row(trial: Trial, project: Project) -> None:
        reviewing = Surveyed(
            number=7, branch="feature", url=_URL, todos=["review"], red=[], threads=0
        )
        healing = Chart(project=project, surveyed=[reviewing])

        assert trial.walk(chart, healing) == Done(Plan(surveyed=[reviewing]))
        assert trial.deltas == []


class TestWholeCast:
    @staticmethod
    @pytest.mark.usefixtures("here")
    def test_mine_surveys_and_writes_nothing(trial: Trial) -> None:
        trial.shell.replies(
            when=LIST, stdout=listing(row(mergeable="MERGEABLE", labels=[]))
        )
        trial.shell.replies(when=board(), stdout=_GREEN)
        trial.shell.replies(when=THREADS, stdout=_NONE)

        result = trial.cast(heal_mine, Heal(plan_only=True))

        assert result == Plan(
            surveyed=[
                Surveyed(
                    number=7,
                    branch="feature",
                    url=_URL,
                    todos=["review"],
                    red=[],
                    threads=0,
                )
            ]
        )
        assert trial.steps == ["muster_mine", "survey", "survey", "chart"]
        # Every other command, a write among them, would have found nothing
        # scripted to answer it.
        assert len(trial.shell.commands) == _READS

    @staticmethod
    @pytest.mark.usefixtures("here")
    def test_this_surveys_the_branch_at_the_cwd(trial: Trial) -> None:
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

    @staticmethod
    @pytest.mark.usefixtures("here")
    def test_only_a_plan_is_cast_so_far(trial: Trial) -> None:
        with pytest.raises(RitualError, match=r"heal\.mine only surveys"):
            trial.cast(heal_mine, Heal())
        with pytest.raises(RitualError, match=r"heal\.this only surveys"):
            trial.cast(heal_this, Heal())
