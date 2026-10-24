"""The review task, how a branch ends, how the cast ends, and whole casts."""

import json
from pathlib import Path

import pytest
from vekna.lexicon import Done, RitualError
from vekna.trial import Trial

from cabinet.gates.ritual.vekna.heal import (
    chart,
    finish_pr,
    quality_review,
    set_aside,
    skip_pr,
    stand_down,
)
from cabinet.pacts.heal import (
    Chart,
    FinishPr,
    QualityReview,
    SetAside,
    SkipPr,
    StandDown,
    Survey,
    Tend,
)
from cabinet.pacts.healing import Checked, Heal, Healed, Run, Surveyed, Work
from cabinet.pacts.project import Project
from cabinet.pacts.pulls import PullRequest
from cabinet.pacts.services import services
from cabinet.pacts.threads import Finding, Findings
from cabinet.rituals.heal_mine import heal_mine
from cabinet.rituals.merge import merge
from cabinet.rituals.review import review
from tests.conftest import (
    HERE,
    LIST,
    STATUS,
    THREADS,
    board,
    commit,
    listing,
    page,
    row,
    threads_page,
)
from tests.integration.rituals.falling import falling

_URL = "https://github.com/o/r/pull/7"
_AHEAD = f'test feature = "$({HERE})" && git rev-list --count origin/feature..HEAD'
_RELEASE = "if git rev-parse*"
_UNMERGED = "git diff --name-only --diff-filter=U"
_LABEL = "gh pr edit 7 --add-label pr::thermo"
_GREEN_ROW = Checked(number=7, branch="feature", url=_URL, outcome="green", unpushed=0)
_NO_THREADS = threads_page(page([]))
_GREEN_BOARD = json.dumps({"total_count": 0, "check_runs": []})


class TestQualityReview:
    @staticmethod
    def test_findings_are_posted_one_by_one_and_the_label_goes_on(
        trial: Trial, work: Work
    ) -> None:
        trial.shell.replies(when=THREADS, stdout=_NO_THREADS)
        trial.coding.replies(
            Findings(
                items=[
                    Finding(path="src/thing.py", line=12, body="guard this"),
                    Finding(path="", body="split the change"),
                ]
            )
        )
        trial.shell.replies(when="gh pr view 7 --json headRefOid*", stdout="abc\n")
        trial.shell.replies(when="gh api repos/*")
        trial.shell.replies(when="gh pr comment 7*")
        trial.shell.replies(when=_LABEL)

        transition = trial.walk(quality_review, work.to(QualityReview))

        assert transition == work.to(Tend)
        assert "Thermo-nuclear code quality review" in trial.coding.prompts[0]
        assert "main...HEAD" in trial.coding.prompts[0]
        assert trial.shell.commands[-3].endswith(
            "-f body='## Thermo-nuclear code quality review\n\nguard this'"
        )
        assert trial.shell.commands[-2] == (
            "gh pr comment 7 --body '## Thermo-nuclear code quality review"
            "\n\nsplit the change'"
        )
        assert trial.shell.commands[-1] == _LABEL
        assert trial.coding.calls[0].focus_options is not None
        assert "Edit" not in str(trial.coding.calls[0].focus_options)

    @staticmethod
    def test_a_review_that_found_nothing_is_still_labelled(
        trial: Trial, work: Work
    ) -> None:
        trial.shell.replies(when=THREADS, stdout=_NO_THREADS)
        trial.coding.replies(Findings(items=[]))
        trial.shell.replies(when=_LABEL)

        assert trial.walk(quality_review, work.to(QualityReview)) == work.to(Tend)
        assert trial.shell.commands[-1] == _LABEL

    @staticmethod
    def test_a_blocked_branch_is_reviewed_and_told_why(
        trial: Trial, work: Work
    ) -> None:
        trial.shell.replies(when=THREADS, stdout=_NO_THREADS)
        trial.coding.replies(Findings(items=[]))
        trial.shell.replies(when=_LABEL)
        blocked = work.stopped_by("red").standing_down("")

        assert trial.walk(quality_review, blocked.to(QualityReview)) == blocked.to(Tend)
        assert "already known not to be green" in trial.coding.prompts[0]

    @staticmethod
    def test_threads_the_forge_would_not_give_set_the_branch_aside(
        trial: Trial, work: Work
    ) -> None:
        trial.shell.replies(when=THREADS, exit_code=1, stderr="502")

        transition = trial.walk(quality_review, work.to(QualityReview))

        assert isinstance(transition, SetAside)
        assert "502" in transition.note
        assert not trial.coding.prompts

    @staticmethod
    def test_an_answer_in_the_wrong_shape_sets_the_branch_aside(
        trial: Trial, work: Work
    ) -> None:
        trial.shell.replies(when=THREADS, stdout=_NO_THREADS)
        trial.coding.replies("no idea, sorry")

        transition = trial.walk(quality_review, work.to(QualityReview))

        assert isinstance(transition, SetAside)
        assert "did not answer in the shape asked" in transition.note

    @staticmethod
    def test_a_review_that_got_nowhere_is_not_labelled(
        trial: Trial, work: Work
    ) -> None:
        trial.shell.replies(when=THREADS, stdout=_NO_THREADS)
        trial.coding.replies(Findings(items=[Finding(path="", body="hm")]))
        trial.shell.replies(when="gh pr comment 7*", exit_code=1, stderr="403")

        assert trial.walk(quality_review, work.to(QualityReview)) == work.but(
            note="0 of 1 review items went up: could not comment on #7: 403"
        ).to(SetAside)
        # No label: the next cast reviews the branch again, which is the whole
        # point of leaving it off.
        assert "--add-label" not in " ".join(trial.shell.commands)

    # The items are up and the label is not, so the next cast reviews the
    # branch again and says all of it twice. Nothing here can prevent that;
    # what it can do is put the forge's complaint in the report.
    @staticmethod
    def test_a_label_the_forge_refuses_sets_the_branch_aside(
        trial: Trial, work: Work
    ) -> None:
        trial.shell.replies(when=THREADS, stdout=_NO_THREADS)
        trial.coding.replies(Findings(items=[Finding(path="", body="hm")]))
        trial.shell.replies(when="gh pr comment 7*")
        trial.shell.replies(when="gh pr edit 7*", exit_code=1, stderr="no such label")

        assert trial.walk(quality_review, work.to(QualityReview)) == work.but(
            note="could not label #7: no such label"
        ).to(SetAside)

    # What is up cannot be taken down, so the label goes on and the report
    # says how far the posting got — the next cast must not say it again.
    @staticmethod
    def test_a_review_that_got_partway_is_labelled_and_counted(
        trial: Trial, work: Work
    ) -> None:
        trial.shell.replies(when=THREADS, stdout=_NO_THREADS)
        trial.coding.replies(
            Findings(items=[Finding(path="", body="one"), Finding(path="", body="two")])
        )
        trial.shell.replies(when="gh pr comment 7 --body '## Thermo*one'")
        trial.shell.replies(
            when="gh pr comment 7 --body '## Thermo*two'", exit_code=1, stderr="403"
        )
        trial.shell.replies(when=_LABEL)

        assert trial.walk(quality_review, work.to(QualityReview)) == work.but(
            note="1 of 2 review items went up: could not comment on #7: 403"
        ).to(SetAside)
        assert trial.shell.commands[-1] == _LABEL

    @staticmethod
    def test_an_agent_that_dies_ends_the_cast(trial: Trial, work: Work) -> None:
        falling()
        trial.shell.replies(when=THREADS, stdout=_NO_THREADS)

        assert trial.walk(quality_review, work.to(QualityReview)) == work.abandoned(
            "the agent stopped mid-flight: boom"
        ).to(Chart)


class TestFinishPr:
    @staticmethod
    def test_a_green_branch_is_counted(trial: Trial, work: Work) -> None:
        trial.shell.replies(when=_AHEAD, stdout="0\n")

        assert trial.walk(finish_pr, work.to(FinishPr)) == work.run.rowed(
            _GREEN_ROW
        ).to(Survey)
        assert trial.shell.commands == [_AHEAD]

    @staticmethod
    def test_a_blocked_branch_says_why(trial: Trial, work: Work) -> None:
        trial.shell.replies(when=_AHEAD, exit_code=1)
        blocked = work.stopped_by("red").standing_down("")

        assert trial.walk(finish_pr, blocked.to(FinishPr)) == blocked.run.rowed(
            _GREEN_ROW.model_copy(
                update={"outcome": "blocked", "unpushed": None, "note": "red"}
            )
        ).to(Survey)


class TestStandDown:
    @staticmethod
    def test_releases_the_worktree_and_tends_on(trial: Trial, work: Work) -> None:
        trial.shell.replies(when=_RELEASE, stdout="stashed\n")
        stopped = work.stopped_by("red").but(todos=["review"])

        assert trial.walk(stand_down, stopped.to(StandDown)) == stopped.standing_down(
            'stashed as "a pr sweep left feature unfinished"'
        ).to(Tend)

    @staticmethod
    def test_a_worktree_that_will_not_release_says_so(trial: Trial, work: Work) -> None:
        trial.shell.replies(when=_RELEASE, exit_code=1, stderr="stuck")

        assert trial.walk(stand_down, work.to(StandDown)) == work.standing_down(
            "the worktree could not be released: stuck"
        ).to(Tend)


class TestSkipPr:
    @staticmethod
    def test_the_row_says_the_branch_was_left_alone(trial: Trial, work: Work) -> None:
        skipped = work.but(note="could not take feature: busy")

        assert trial.walk(skip_pr, skipped.to(SkipPr)) == work.run.rowed(
            _GREEN_ROW.model_copy(
                update={
                    "outcome": "skipped",
                    "unpushed": None,
                    "note": "could not take feature: busy",
                }
            )
        ).to(Survey)


class TestSetAside:
    @staticmethod
    def test_releases_counts_and_reports_blocked(trial: Trial, work: Work) -> None:
        trial.shell.replies(when=_RELEASE, stdout="stashed\n")
        trial.shell.replies(when=_AHEAD, stdout="2\n")
        aside = work.stopped_by("red").but(note="gh died")

        transition = trial.walk(set_aside, aside.to(SetAside))

        assert transition == work.run.rowed(
            _GREEN_ROW.model_copy(
                update={
                    "outcome": "blocked",
                    "unpushed": 2,
                    "note": (
                        "red; gh died;"
                        ' stashed as "a pr sweep left feature unfinished"'
                    ),
                }
            )
        ).to(Survey)
        assert trial.shell.commands[0].startswith("if git rev-parse")
        assert trial.shell.commands[1] == _AHEAD


class TestChart:
    @staticmethod
    def test_the_summary_is_said_and_the_result_returned(
        trial: Trial, project: Project
    ) -> None:
        run = Run(project=project, checked=[_GREEN_ROW])

        assert trial.walk(chart, run.to(Chart)) == Done(Healed(checked=[_GREEN_ROW]))
        assert trial.deltas[0].startswith("heal — 1 worked")

    @staticmethod
    def test_a_plan_says_nothing_past_its_survey(
        trial: Trial, project: Project
    ) -> None:
        planned = Surveyed(
            number=7, branch="feature", url=_URL, todos=["review"], red=[], threads=0
        )
        run = Run(project=project, plan_only=True, surveyed=[planned])

        assert trial.walk(chart, run.to(Chart)) == Done(Healed(surveyed=[planned]))
        assert trial.deltas == []

    @staticmethod
    def test_a_cast_out_of_steps_ends_without_failing(
        trial: Trial, project: Project, pull: PullRequest
    ) -> None:
        run = Run(project=project, queue=[pull])

        assert trial.walk(chart, run.to(Chart)) == Done(Healed(not_reached=["feature"]))
        assert "left for the next cast: feature" in trial.deltas[0]

    @staticmethod
    def test_a_stopped_cast_is_said_before_it_fails(
        trial: Trial, project: Project
    ) -> None:
        run = Run(project=project, plan_only=True, stopped="gh died")

        with pytest.raises(RitualError, match="gh died"):
            trial.walk(chart, run.to(Chart))

        assert "the cast failed: gh died" in trial.deltas[0]


# The forge's listing and git's preflight, the branch taken, and the count at
# the end: what every acting cast here walks through.
def _taken(trial: Trial, *, mergeable: str) -> None:
    trial.shell.replies(
        when="git remote get-url origin", stdout="https://github.com/o/r.git\n"
    )
    trial.shell.replies(when="git config --get-urlmatch*", stdout="!gh auth\n")
    trial.shell.replies(when=LIST, stdout=listing(row(7, mergeable=mergeable)))
    trial.shell.replies(when=board(), stdout=_GREEN_BOARD)
    trial.shell.replies(when=THREADS, stdout=_NO_THREADS, always=True)
    trial.shell.replies(when=STATUS, always=True)
    trial.shell.replies(when="git fetch*")
    trial.shell.replies(when="git checkout feature")
    trial.shell.replies(when="git merge --ff-only*")
    trial.shell.replies(when=_AHEAD, stdout="0\n")


# A conflict an agent resolves in one round.
def _conflicted(trial: Trial) -> None:
    trial.shell.replies(when="git merge-base*", exit_code=1)
    trial.shell.replies(when="git merge --no-edit main", exit_code=1)
    trial.shell.replies(when=_UNMERGED, stdout="a.py\n")
    trial.shell.replies(when=_UNMERGED)
    trial.coding.replies("resolved", when="Merging main into feature*")


def _reviewed(trial: Trial) -> None:
    trial.coding.replies(Findings(items=[]), when="Review the changes*")
    trial.shell.replies(when=_LABEL)


# The whole gate red, a repair, the task it named green, round to the bound,
# then red once more and stood down.
def _worst_gate(trial: Trial, bound: int) -> None:
    red = "[lint:ruff] ERROR task failed"
    for _ in range(bound + 1):
        trial.shell.replies(
            when="CI=1 mise run pr-fix", exit_code=1, stdout="E501", stderr=red
        )
    trial.shell.replies(when="CI=1 mise run lint:ruff", always=True)
    trial.coding.replies("fixed", when="*is this project's gate*", always=True)


class TestWholeCast:
    @staticmethod
    @pytest.mark.usefixtures("here")
    def test_mine_merges_pushes_and_reviews(trial: Trial) -> None:
        _taken(trial, mergeable="CONFLICTING")
        _conflicted(trial)
        trial.shell.replies(when="CI=1 mise run pr-fix")
        trial.shell.replies(when=_RELEASE, always=True)
        trial.shell.replies(when="git add -A*")
        trial.shell.replies(when="git push origin feature")
        _reviewed(trial)

        result = trial.cast(heal_mine, Heal())

        assert result.checked == [_GREEN_ROW]
        assert result.surveyed[0] == Surveyed(
            number=7,
            branch="feature",
            url=_URL,
            todos=["merge", "review"],
            red=[],
            threads=0,
        )
        assert trial.steps == [
            "muster_mine",
            "survey",
            "check_clean",
            "sync_branch",
            "tend",
            "merge_base",
            "resolve_conflicts",
            "resolve_conflicts",
            "gate_check",
            "finish_merge",
            "tend",
            "push_work",
            "tend",
            "quality_review",
            "tend",
            "finish_pr",
            "survey",
            "chart",
        ]
        commands = trial.shell.commands
        assert commands.index("git push origin feature") < commands.index(_LABEL)
        assert commit("chore: merge main and fix the gates") in commands

    # Nothing this cast works: surveyed, said, and never checked out.
    @staticmethod
    @pytest.mark.usefixtures("here")
    def test_a_branch_with_nothing_to_work_is_not_taken(trial: Trial) -> None:
        trial.shell.replies(
            when="git remote get-url origin", stdout="https://github.com/o/r.git\n"
        )
        trial.shell.replies(when="git config --get-urlmatch*", stdout="!gh auth\n")
        trial.shell.replies(
            when=LIST,
            stdout=listing(
                row(7, mergeable="MERGEABLE", labels=[{"name": "pr::thermo"}])
            ),
        )
        trial.shell.replies(when=board(), stdout=_GREEN_BOARD)
        trial.shell.replies(when=THREADS, stdout=_NO_THREADS)

        result = trial.cast(heal_mine, Heal())

        assert result.checked == []
        assert trial.steps == ["muster_mine", "survey", "survey", "chart"]
        assert trial.deltas[0] == "#7 feature: guide"

    # Every attempt the bound allows on both loops, each with its free extra
    # run, the stand-down, and the review after it: the longest a branch can
    # run, and what its share spoke for.
    @staticmethod
    @pytest.mark.usefixtures("here")
    @pytest.mark.parametrize("bound", [1, 2])
    def test_the_worst_a_branch_can_spend_is_what_was_reserved(
        trial: Trial, bound: int
    ) -> None:
        _taken(trial, mergeable="CONFLICTING")
        trial.shell.replies(when="git merge-base*", exit_code=1)
        trial.shell.replies(when="git merge --no-edit main", exit_code=1)
        for _ in range(bound):
            trial.shell.replies(when=_UNMERGED, stdout="a.py\n")
        trial.shell.replies(when=_UNMERGED)
        trial.coding.replies("resolved", when="Merging main into feature*", always=True)
        trial.shell.replies(when=_RELEASE, always=True)
        trial.shell.replies(when="git push origin feature")
        _worst_gate(trial, bound)
        _reviewed(trial)

        result = trial.cast(heal_mine, Heal(bound=bound))

        assert [one.outcome for one in result.checked] == ["blocked"]
        assert trial.steps == [
            "muster_mine",
            "survey",
            "check_clean",
            "sync_branch",
            "tend",
            "merge_base",
            *["resolve_conflicts"] * (bound + 1),
            *["gate_check"] * (2 * bound + 1),
            "stand_down",
            "tend",
            "push_work",
            "tend",
            "quality_review",
            "tend",
            "finish_pr",
            "survey",
            "chart",
        ]
        share = services().steps.heal_share(Run(project=Project(), bound=bound))
        assert share is not None
        assert len(trial.steps) == services().steps.opening(1) + share

    @staticmethod
    def test_a_gitlab_project_speaks_glab(trial: Trial, here: Path) -> None:
        (here / ".vekna.toml").write_text('[cabinet]\nforge = "gitlab"\n')
        trial.shell.replies(
            when="git remote get-url origin", stdout="https://gitlab.example/o/r.git\n"
        )
        trial.shell.replies(when="git config --get-urlmatch*", stdout="!glab auth\n")
        trial.shell.replies(when="glab api 'projects/:id/merge_requests?*", stdout="[]")

        result = trial.cast(heal_mine, Heal())

        assert result == Healed()
        assert trial.shell.commands[-1].startswith("glab api")
        assert trial.steps == ["muster_mine", "survey", "chart"]


class TestTaskRituals:
    @staticmethod
    @pytest.mark.usefixtures("here")
    def test_merge_works_the_merge_and_leaves_the_review(trial: Trial) -> None:
        _taken(trial, mergeable="CONFLICTING")
        trial.shell.replies(when=HERE, stdout="feature\n")
        _conflicted(trial)
        trial.shell.replies(when="CI=1 mise run pr-fix")
        trial.shell.replies(when=_RELEASE, always=True)
        trial.shell.replies(when="git add -A*")
        trial.shell.replies(when="git push origin feature")

        result = trial.cast(merge, Heal())

        assert result.checked == [_GREEN_ROW]
        assert trial.steps == [
            "muster_this",
            "survey",
            "check_clean",
            "sync_branch",
            "tend",
            "merge_base",
            "resolve_conflicts",
            "resolve_conflicts",
            "gate_check",
            "finish_merge",
            "tend",
            "push_work",
            "tend",
            "finish_pr",
            "survey",
            "chart",
        ]

    @staticmethod
    @pytest.mark.usefixtures("here")
    def test_review_reviews_and_leaves_the_conflict(trial: Trial) -> None:
        _taken(trial, mergeable="CONFLICTING")
        trial.shell.replies(when=HERE, stdout="feature\n")
        _reviewed(trial)

        result = trial.cast(review, Heal())

        assert result.checked == [_GREEN_ROW]
        assert trial.steps == [
            "muster_this",
            "survey",
            "check_clean",
            "sync_branch",
            "tend",
            "quality_review",
            "tend",
            "finish_pr",
            "survey",
            "chart",
        ]
