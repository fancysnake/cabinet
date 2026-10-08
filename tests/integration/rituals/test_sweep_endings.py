"""How a branch ends, how the night ends, and a whole night at once."""

import json
from collections.abc import Callable
from pathlib import Path

import pytest
from vekna.lexicon import Done, RitualError
from vekna.trial import Trial

from cabinet.gates.ritual.vekna.sweep import (
    finish_pr,
    quality_review,
    report,
    set_aside,
    skip_pr,
    stand_down,
)
from cabinet.pacts.project import Project
from cabinet.pacts.pulls import Checked, Closed, PullRequest, Report, Run, Sweep, Work
from cabinet.pacts.services import services
from cabinet.pacts.sweep import (
    NextPr,
    PushWork,
    QualityReview,
    Reporting,
    SetAside,
    SkipPr,
    StandDown,
)
from cabinet.pacts.threads import Finding, Findings
from cabinet.rituals.cover import cover
from cabinet.rituals.refresh import refresh
from tests.conftest import (
    HERE,
    LABELS,
    LIST,
    STATUS,
    THREADS,
    board,
    checkpoint,
    commit,
    listing,
    page,
    row,
    threads_page,
)
from tests.integration.rituals.falling import falling

_DONE = checkpoint("refresh", "done")
_COVER_DONE = checkpoint("cover", "done")
_AHEAD = f'test feature = "$({HERE})" && git rev-list --count origin/feature..HEAD'
_RELEASE = "if git rev-parse*"
_UNMERGED = "git diff --name-only --diff-filter=U"
_MISSING = """Diff Coverage
-------------
src/thing.py (80.0%): Missing lines 12-14
-------------
Total:   10 lines
Missing: 3 lines
-------------
"""
_COVERED = "Diff Coverage\n-------------\nTotal:   10 lines\nMissing: 0 lines\n"
_GREEN_ROW = Checked(
    number=7,
    branch="feature",
    url="https://github.com/o/r/pull/7",
    outcome="green",
    unpushed=0,
)
_NO_THREADS = threads_page(page([]))
_GREEN_BOARD = json.dumps(
    {
        "total_count": 3,
        "check_runs": [
            {"name": "checks", "conclusion": "success"},
            {"name": "test", "conclusion": "success"},
            {
                "name": "codecov/patch",
                "conclusion": "success",
                "output": {"title": "100.00% of diff hit"},
            },
        ],
    }
)


def _labels(*names: str) -> str:
    return json.dumps({"labels": [{"name": name} for name in names]})


class TestQualityReview:
    @staticmethod
    def test_a_branch_already_reviewed_is_left_alone(trial: Trial, work: Work) -> None:
        trial.shell.replies(when=LABELS, stdout=_labels("pr::thermo"))

        assert trial.walk(quality_review, work.to(QualityReview)) == Closed(
            work=work, outcome="green"
        )
        assert trial.shell.commands == [LABELS]
        assert not trial.coding.prompts

    @staticmethod
    def test_findings_are_posted_one_by_one_and_the_label_goes_on(
        trial: Trial, work: Work
    ) -> None:
        trial.shell.replies(when=LABELS, stdout=_labels("bug"))
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
        trial.shell.replies(when="gh pr edit 7 --add-label pr::thermo")

        transition = trial.walk(quality_review, work.to(QualityReview))

        assert transition == Closed(work=work, outcome="green")
        assert "Thermo-nuclear code quality review" in trial.coding.prompts[0]
        assert "main...HEAD" in trial.coding.prompts[0]
        assert trial.shell.commands[-3].endswith(
            "-f body='## Thermo-nuclear code quality review\n\nguard this'"
        )
        assert trial.shell.commands[-2] == (
            "gh pr comment 7 --body '## Thermo-nuclear code quality review"
            "\n\nsplit the change'"
        )
        assert trial.shell.commands[-1] == "gh pr edit 7 --add-label pr::thermo"
        assert trial.coding.calls[0].focus_options is not None
        assert "Edit" not in str(trial.coding.calls[0].focus_options)

    @staticmethod
    def test_a_review_that_found_nothing_is_still_labelled(
        trial: Trial, work: Work
    ) -> None:
        trial.shell.replies(when=LABELS, stdout=_labels())
        trial.shell.replies(when=THREADS, stdout=_NO_THREADS)
        trial.coding.replies(Findings(items=[]))
        trial.shell.replies(when="gh pr edit 7 --add-label pr::thermo")

        assert trial.walk(quality_review, work.to(QualityReview)) == Closed(
            work=work, outcome="green"
        )

    @staticmethod
    def test_a_blocked_branch_is_reviewed_and_told_why(
        trial: Trial, work: Work
    ) -> None:
        trial.shell.replies(when=LABELS, stdout=_labels())
        trial.shell.replies(when=THREADS, stdout=_NO_THREADS)
        trial.coding.replies(Findings(items=[]))
        trial.shell.replies(when="gh pr edit 7 --add-label pr::thermo")
        blocked = work.stopped_by("red").standing_down("")

        assert trial.walk(quality_review, blocked.to(QualityReview)) == Closed(
            work=blocked, outcome="blocked"
        )
        assert "already known not to be green" in trial.coding.prompts[0]

    @staticmethod
    def test_labels_the_forge_would_not_give_set_the_branch_aside(
        trial: Trial, work: Work
    ) -> None:
        trial.shell.replies(when=LABELS, exit_code=1, stderr="502")

        assert trial.walk(quality_review, work.to(QualityReview)) == work.but(
            note="gh could not read the labels: 502"
        ).to(SetAside)

    @staticmethod
    def test_an_answer_in_the_wrong_shape_sets_the_branch_aside(
        trial: Trial, work: Work
    ) -> None:
        trial.shell.replies(when=LABELS, stdout=_labels())
        trial.shell.replies(when=THREADS, stdout=_NO_THREADS)
        trial.coding.replies("no idea, sorry")

        transition = trial.walk(quality_review, work.to(QualityReview))

        assert isinstance(transition, SetAside)
        assert "did not answer in the shape asked" in transition.note

    @staticmethod
    def test_a_review_that_got_nowhere_is_not_labelled(
        trial: Trial, work: Work
    ) -> None:
        trial.shell.replies(when=LABELS, stdout=_labels())
        trial.shell.replies(when=THREADS, stdout=_NO_THREADS)
        trial.coding.replies(Findings(items=[Finding(path="", body="hm")]))
        trial.shell.replies(when="gh pr comment 7*", exit_code=1, stderr="403")

        assert trial.walk(quality_review, work.to(QualityReview)) == work.but(
            note="0 of 1 review items went up: could not comment on #7: 403"
        ).to(SetAside)
        # No label: the branch is read again tomorrow, which is the whole
        # point of leaving it off.
        assert "--add-label" not in " ".join(trial.shell.commands)

    # The items are up and the label is not, so the next night reviews the
    # branch again and says all of it twice. Nothing here can prevent that;
    # what it can do is put the forge's complaint in front of the morning.
    @staticmethod
    def test_a_label_the_forge_refuses_sets_the_branch_aside(
        trial: Trial, work: Work
    ) -> None:
        trial.shell.replies(when=LABELS, stdout=_labels())
        trial.shell.replies(when=THREADS, stdout=_NO_THREADS)
        trial.coding.replies(Findings(items=[Finding(path="", body="hm")]))
        trial.shell.replies(when="gh pr comment 7*")
        trial.shell.replies(when="gh pr edit 7*", exit_code=1, stderr="no such label")

        assert trial.walk(quality_review, work.to(QualityReview)) == work.but(
            note="could not label #7: no such label"
        ).to(SetAside)

    # What is up cannot be taken down, so the label goes on and the morning is
    # told how far the posting got — the next night must not say it again.
    @staticmethod
    def test_a_review_that_got_partway_is_labelled_and_counted(
        trial: Trial, work: Work
    ) -> None:
        trial.shell.replies(when=LABELS, stdout=_labels())
        trial.shell.replies(when=THREADS, stdout=_NO_THREADS)
        trial.coding.replies(
            Findings(items=[Finding(path="", body="one"), Finding(path="", body="two")])
        )
        trial.shell.replies(when="gh pr comment 7 --body '## Thermo*one'")
        trial.shell.replies(
            when="gh pr comment 7 --body '## Thermo*two'", exit_code=1, stderr="403"
        )
        trial.shell.replies(when="gh pr edit 7 --add-label pr::thermo")

        assert trial.walk(quality_review, work.to(QualityReview)) == work.but(
            note="1 of 2 review items went up: could not comment on #7: 403"
        ).to(SetAside)
        assert trial.shell.commands[-1] == "gh pr edit 7 --add-label pr::thermo"

    @staticmethod
    def test_an_agent_that_dies_ends_the_run(trial: Trial, work: Work) -> None:
        falling()
        trial.shell.replies(when=LABELS, stdout=_labels())
        trial.shell.replies(when=THREADS, stdout=_NO_THREADS)

        assert trial.walk(quality_review, work.to(QualityReview)) == work.abandoned(
            "the agent stopped mid-flight: boom"
        ).to(Reporting)


class TestFinishPr:
    @staticmethod
    def test_a_green_branch_is_marked_done_and_counted(
        trial: Trial, work: Work
    ) -> None:
        trial.shell.replies(when="gh pr edit 7*")
        trial.shell.replies(when=_AHEAD, stdout="0\n")

        assert trial.walk(
            finish_pr, Closed(work=work, outcome="green")
        ) == work.run.rowed(_GREEN_ROW).to(NextPr)
        assert trial.shell.commands == [_DONE, _AHEAD]

    @staticmethod
    def test_a_blocked_branch_keeps_started(trial: Trial, work: Work) -> None:
        trial.shell.replies(when=_AHEAD, exit_code=1)
        blocked = work.stopped_by("red").standing_down("")

        transition = trial.walk(finish_pr, Closed(work=blocked, outcome="blocked"))

        assert transition == blocked.run.rowed(
            _GREEN_ROW.model_copy(
                update={"outcome": "blocked", "unpushed": None, "note": "red"}
            )
        ).to(NextPr)
        assert trial.shell.commands == [_AHEAD]

    @staticmethod
    def test_a_checkpoint_that_will_not_go_on_is_in_the_note(
        trial: Trial, work: Work
    ) -> None:
        trial.shell.replies(when="gh pr edit 7*", exit_code=1, stderr="no label")
        trial.shell.replies(when=_AHEAD, stdout="0\n")

        transition = trial.walk(finish_pr, Closed(work=work, outcome="green"))

        assert transition == work.run.rowed(
            _GREEN_ROW.model_copy(
                update={
                    "note": (
                        "could not mark v:refresh:done: could not label #7: no label"
                    )
                }
            )
        ).to(NextPr)


class TestStandDown:
    @staticmethod
    def test_releases_the_worktree_and_reads_on(trial: Trial, work: Work) -> None:
        trial.shell.replies(when=_RELEASE, stdout="stashed\n")
        stopped = work.stopped_by("red")

        assert trial.walk(stand_down, stopped.to(StandDown)) == stopped.standing_down(
            'stashed as "a pr sweep left feature unfinished"'
        ).to(PushWork)

    @staticmethod
    def test_a_worktree_that_will_not_release_says_so(trial: Trial, work: Work) -> None:
        trial.shell.replies(when=_RELEASE, exit_code=1, stderr="stuck")

        assert trial.walk(stand_down, work.to(StandDown)) == work.standing_down(
            "the worktree could not be released: stuck"
        ).to(PushWork)


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
        ).to(NextPr)


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
        ).to(NextPr)
        assert trial.shell.commands[0].startswith("if git rev-parse")
        assert trial.shell.commands[1] == _AHEAD


class TestReport:
    @staticmethod
    def test_the_summary_is_said_and_the_card_returned(
        trial: Trial, project: Project
    ) -> None:
        run = Run(project=project, bound=3, checked=[_GREEN_ROW])

        assert trial.walk(report, run.to(Reporting)) == Done(
            Report(checked=[_GREEN_ROW])
        )

    @staticmethod
    def test_a_run_out_of_steps_ends_without_failing(
        trial: Trial, project: Project, pull: PullRequest
    ) -> None:
        run = Run(project=project, bound=3, queue=[pull])

        assert trial.walk(report, run.to(Reporting)) == Done(
            Report(not_reached=["feature"])
        )
        assert "left for the next run: feature" in trial.deltas[0]

    @staticmethod
    def test_a_stopped_run_is_said_before_it_fails(
        trial: Trial, project: Project
    ) -> None:
        run = Run(project=project, bound=3, stopped="gh died")

        with pytest.raises(RitualError, match="gh died"):
            trial.walk(report, run.to(Reporting))

        assert "the run failed: gh died" in trial.deltas[0]


# `refresh`'s worst after `take_pass`: the whole gate red, a repair, the task it
# named green, round to the bound, then red once more and stood down. Answers
# with the steps that walks.
def _worst_gate(trial: Trial, bound: int) -> list[str]:
    red = "[lint:ruff] ERROR task failed"
    for _ in range(bound + 1):
        trial.shell.replies(
            when="CI=1 mise run pr-fix", exit_code=1, stdout="E501", stderr=red
        )
    trial.shell.replies(when="CI=1 mise run lint:ruff", always=True)
    trial.coding.replies("fixed", when="*is this project's gate*", always=True)
    trial.shell.replies(when=LABELS, stdout=_labels("pr::thermo"))
    gates = ["gate_check"] * (2 * bound + 1)
    return [*gates, "stand_down", "push_work", "quality_review"]


# `cover`'s worst after `take_pass`: lines missing, a test written, the fast
# measurement covered, round to the bound, then missing once more and stood
# down. Answers with the steps that walks.
def _worst_gap(trial: Trial, bound: int) -> list[str]:
    trial.shell.replies(when=board(), exit_code=1, stderr="no board")
    for _ in range(bound + 1):
        trial.shell.replies(when="CI=1 mise run diff-cover", stdout=_MISSING)
    trial.shell.replies(
        when="CI=1 mise run test:py:cov:diff", stdout=_COVERED, always=True
    )
    trial.coding.replies("wrote a test", when="*Missing lines*", always=True)
    gaps = ["close_gap"] * (2 * bound + 1)
    return ["finish_merge", "check_ci", *gaps, "stand_down", "push_work"]


_PASSES = {"refresh": refresh, "cover": cover}

# Each pass, its worst walk, and how far under its share that walk falls:
# `refresh` stands down out of the gate's loop, before `finish_merge`, so it
# never walks both, and `check_ci` is `cover`'s alone.
_WORST = [
    pytest.param("refresh", _worst_gate, 1, id="refresh"),
    pytest.param("cover", _worst_gap, 0, id="cover"),
]


class TestWholeCast:
    @staticmethod
    def _night(trial: Trial) -> None:
        trial.shell.replies(
            when="git remote get-url origin", stdout="https://github.com/o/r.git\n"
        )
        trial.shell.replies(when="git config --get-urlmatch*", stdout="!gh auth\n")
        trial.shell.replies(when=LIST, stdout=listing(row(7)))
        trial.shell.replies(when=STATUS, always=True)
        trial.shell.replies(when="git fetch*")
        trial.shell.replies(when="git checkout feature")
        trial.shell.replies(when="git merge --ff-only*")
        trial.shell.replies(when="gh pr edit 7*", always=True)
        trial.shell.replies(when="git merge-base*", exit_code=1)
        trial.shell.replies(when="git merge --no-edit main")
        trial.shell.replies(when="git add -A*", always=True)
        trial.shell.replies(when="git push origin feature")
        trial.shell.replies(when=_AHEAD, stdout="0\n")

    @pytest.mark.usefixtures("here")
    def test_the_fast_pass_merges_repairs_pushes_and_reviews(
        self, trial: Trial
    ) -> None:
        self._night(trial)
        trial.shell.replies(when="CI=1 mise run pr-fix", exit_code=1, stdout="1 failed")
        trial.coding.replies("fixed", when="*is this project's gate*")
        trial.shell.replies(when="CI=1 mise run pr-fix")
        trial.shell.replies(when=LABELS, stdout=_labels())
        trial.shell.replies(when=THREADS, stdout=_NO_THREADS)
        trial.coding.replies(Findings(items=[]), when="Review the changes*")

        result = trial.cast(refresh, Sweep(bound=3))

        assert result == Report(checked=[_GREEN_ROW])
        assert trial.steps == [
            "list_prs",
            "next_pr",
            "check_clean",
            "sync_branch",
            "merge_base",
            "take_pass",
            "gate_check",
            "gate_check",
            "finish_merge",
            "push_work",
            "quality_review",
            "finish_pr",
            "next_pr",
            "report",
        ]
        assert commit("chore: merge main and fix the gates") in trial.shell.commands
        assert trial.shell.commands[-2] == _DONE
        assert trial.coding.calls[0].resume is None
        assert "CI=1 mise run diff-cover" not in trial.shell.commands

    @pytest.mark.usefixtures("here")
    def test_the_slow_pass_skips_a_branch_ci_is_happy_with(self, trial: Trial) -> None:
        self._night(trial)
        trial.shell.replies(when=board(), stdout=_GREEN_BOARD)

        result = trial.cast(cover, Sweep(bound=3))

        assert result == Report(
            checked=[
                _GREEN_ROW.model_copy(
                    update={"note": "coverage and the suite are green on CI"}
                )
            ]
        )
        assert trial.steps == [
            "list_prs",
            "next_pr",
            "check_clean",
            "sync_branch",
            "merge_base",
            "take_pass",
            "finish_merge",
            "check_ci",
            "push_work",
            "finish_pr",
            "next_pr",
            "report",
        ]
        assert "CI=1 mise run pr-fix" not in trial.shell.commands
        assert trial.shell.commands[-2] == _COVER_DONE
        assert not trial.coding.prompts

    # Every attempt the bound allows on both loops, each with its free extra
    # run, and the stand-down after the pass's own loop: the longest a branch
    # can run, and what its share spoke for.
    @staticmethod
    @pytest.mark.usefixtures("here")
    @pytest.mark.parametrize("bound", [1, 2])
    @pytest.mark.parametrize(("mode", "loop", "spare"), _WORST)
    def test_the_worst_a_branch_can_spend_is_what_was_reserved(
        trial: Trial,
        mode: str,
        loop: Callable[[Trial, int], list[str]],
        spare: int,
        bound: int,
    ) -> None:
        trial.shell.replies(
            when="git remote get-url origin", stdout="https://github.com/o/r.git\n"
        )
        trial.shell.replies(when="git config --get-urlmatch*", stdout="!gh auth\n")
        trial.shell.replies(when=LIST, stdout=listing(row(7)))
        trial.shell.replies(when=STATUS, always=True)
        trial.shell.replies(when="git fetch*")
        trial.shell.replies(when="git checkout feature")
        trial.shell.replies(when="git merge --ff-only*")
        trial.shell.replies(when="gh pr edit 7*", always=True)
        trial.shell.replies(when="git merge-base*", exit_code=1)
        trial.shell.replies(when="git merge --no-edit main", exit_code=1)
        trial.shell.replies(when="git add -A*", always=True)
        trial.shell.replies(when="git push origin feature")
        trial.shell.replies(when=_AHEAD, stdout="0\n")
        for _ in range(bound):
            trial.shell.replies(when=_UNMERGED, stdout="a.py\n")
        trial.shell.replies(when=_UNMERGED)
        trial.coding.replies("resolved", when="Merging main into feature*", always=True)
        trial.shell.replies(when="if git rev-parse*", always=True)

        walked = loop(trial, bound)

        result = trial.cast(_PASSES[mode], Sweep(bound=bound))

        assert [row.outcome for row in result.checked] == ["blocked"]
        assert trial.steps == [
            "list_prs",
            "next_pr",
            "check_clean",
            "sync_branch",
            "merge_base",
            *["resolve_conflicts"] * (bound + 1),
            "take_pass",
            *walked,
            "finish_pr",
            "next_pr",
            "report",
        ]
        share = services().steps.sweep_share(Run(project=Project(), bound=bound))
        assert share is not None
        assert len(trial.steps) == services().steps.opening(1) + share - spare

    @staticmethod
    def test_a_gitlab_project_speaks_glab(trial: Trial, here: Path) -> None:
        (here / ".vekna.toml").write_text('[cabinet]\nforge = "gitlab"\n')
        trial.shell.replies(
            when="git remote get-url origin", stdout="https://gitlab.example/o/r.git\n"
        )
        trial.shell.replies(when="git config --get-urlmatch*", stdout="!glab auth\n")
        trial.shell.replies(when="glab api 'projects/:id/merge_requests?*", stdout="[]")

        result = trial.cast(refresh, Sweep(bound=3))

        assert result == Report()
        assert trial.shell.commands[-1].startswith("glab api")
        assert trial.steps == ["list_prs", "next_pr", "report"]
