"""Taking a branch: listing, standing on it, merging the base in."""

from typing import TYPE_CHECKING

from vekna.lexicon import Goto, goto

from cabinet.gates.ritual.vekna.sweep import (
    check_clean,
    list_prs,
    merge_base,
    next_pr,
    report,
    resolve_conflicts,
    set_aside,
    skip_pr,
    stand_down,
    sync_branch,
    take_pass,
)
from cabinet.pacts.pulls import PullRequest, Run, Work
from tests.conftest import LIST, STATUS, checkpoint, listing, row
from tests.integration.rituals.falling import falling

if TYPE_CHECKING:
    from vekna.trial import Trial

    from cabinet.pacts.project import Project

_STARTED = checkpoint("refresh", "started")
_UNMERGED = "git diff --name-only --diff-filter=U"
_IS_ANCESTOR = "git merge-base --is-ancestor main HEAD"
_MERGE = "git merge --no-edit main"


def _preflight(trial: Trial) -> None:
    trial.shell.replies(
        when="git remote get-url origin", stdout="https://github.com/o/r.git\n"
    )
    trial.shell.replies(when="git config --get-urlmatch*", stdout="!gh auth\n")


class TestListPrs:
    @staticmethod
    def test_queues_what_is_wanted_oldest_first(trial: Trial, project: Project) -> None:
        _preflight(trial)
        newer = row(8, updatedAt="2026-08-02T00:00:00Z")
        parked = row(9, labels=[{"name": "pr::wait"}])
        trial.shell.replies(when=LIST, stdout=listing(newer, row(7), parked))

        transition = trial.walk(list_prs, Run(project=project, bound=3))

        assert isinstance(transition, Goto)
        assert transition.target is next_pr
        assert isinstance(transition.payload, Run)
        assert [pull.number for pull in transition.payload.queue] == [7, 8]

    @staticmethod
    def test_a_forge_that_will_not_answer_ends_in_the_report(
        trial: Trial, project: Project
    ) -> None:
        _preflight(trial)
        trial.shell.replies(when=LIST, exit_code=1, stderr="not logged in")

        transition = trial.walk(list_prs, Run(project=project, bound=3))

        assert transition == goto(
            report,
            Run(
                project=project,
                bound=3,
                stopped="gh could not list your pull requests: not logged in",
            ),
        )

    @staticmethod
    def test_an_ssh_remote_stops_before_anything_is_fetched(
        trial: Trial, project: Project
    ) -> None:
        trial.shell.replies(
            when="git remote get-url origin", stdout="git@github.com:o/r.git\n"
        )

        transition = trial.walk(list_prs, Run(project=project, bound=3))

        assert isinstance(transition, Goto)
        assert transition.target is report
        assert isinstance(transition.payload, Run)
        assert "not https" in transition.payload.stopped
        assert LIST not in trial.shell.commands


class TestNextPr:
    @staticmethod
    def test_an_empty_queue_is_the_report(trial: Trial, project: Project) -> None:
        run = Run(project=project, bound=3)

        assert trial.walk(next_pr, run) == goto(report, run)

    @staticmethod
    def test_takes_the_first_with_a_fresh_work(
        trial: Trial, project: Project, pull: PullRequest
    ) -> None:
        other = pull.model_copy(update={"number": 8, "branch": "feature-8"})
        run = Run(project=project, bound=3, queue=[pull, other])

        assert trial.walk(next_pr, run) == goto(
            check_clean, Work(run=run.but(queue=[other]), pr=pull)
        )


class TestCheckClean:
    @staticmethod
    def test_a_clean_tree_goes_on(trial: Trial, work: Work) -> None:
        trial.shell.replies(when=STATUS)

        assert trial.walk(check_clean, work) == goto(sync_branch, work)

    @staticmethod
    def test_a_dirty_tree_ends_the_run(trial: Trial, work: Work) -> None:
        trial.shell.replies(when=STATUS, stdout=" M a.py\n")

        transition = trial.walk(check_clean, work)

        assert transition == goto(
            report, work.abandoned("the worktree is not clean:\nM a.py")
        )

    @staticmethod
    def test_a_status_that_fails_ends_the_run(trial: Trial, work: Work) -> None:
        trial.shell.replies(when=STATUS, exit_code=128, stderr="not a repo")

        assert trial.walk(check_clean, work) == goto(
            report, work.abandoned("git status failed: not a repo")
        )


class TestSyncBranch:
    @staticmethod
    def test_updates_the_base_then_stands_on_the_branch(
        trial: Trial, work: Work
    ) -> None:
        trial.shell.replies(when="git fetch*")
        trial.shell.replies(when="git checkout feature")
        trial.shell.replies(when="git merge --ff-only*")

        assert trial.walk(sync_branch, work) == goto(merge_base, work)
        assert trial.shell.commands == [
            (
                "git fetch --prune origin && git checkout main"
                " && git pull --ff-only origin main"
            ),
            "git checkout feature",
            "git merge --ff-only origin/feature",
        ]

    @staticmethod
    def test_a_base_that_will_not_update_ends_the_run(trial: Trial, work: Work) -> None:
        trial.shell.replies(when="git fetch*", exit_code=1, stderr="no network")

        assert trial.walk(sync_branch, work) == goto(
            report, work.abandoned("could not update main: no network")
        )

    @staticmethod
    def test_a_checkout_that_will_not_go_through_skips_the_branch(
        trial: Trial, work: Work
    ) -> None:
        trial.shell.replies(when="git fetch*")
        trial.shell.replies(when="git checkout feature", exit_code=1, stderr="busy")

        assert trial.walk(sync_branch, work) == goto(
            skip_pr, work.but(note="could not take feature: busy")
        )

    @staticmethod
    def test_a_diverged_branch_is_set_aside(trial: Trial, work: Work) -> None:
        trial.shell.replies(when="git fetch*")
        trial.shell.replies(when="git checkout feature")
        trial.shell.replies(when="git merge --ff-only*", exit_code=1, stderr="diverged")

        assert trial.walk(sync_branch, work) == goto(
            set_aside, work.but(note="could not catch up with the remote: diverged")
        )


class TestMergeBase:
    @staticmethod
    def test_marks_started_before_the_merge(trial: Trial, work: Work) -> None:
        trial.shell.replies(when="gh pr edit 7*")
        trial.shell.replies(when=_IS_ANCESTOR, exit_code=1)
        trial.shell.replies(when=_MERGE)

        transition = trial.walk(merge_base, work)

        assert transition == goto(take_pass, work.graded(unchanged=False))
        assert trial.shell.commands == [_STARTED, _IS_ANCESTOR, _MERGE]

    @staticmethod
    def test_a_base_already_contained_is_an_unchanged_tree(
        trial: Trial, work: Work
    ) -> None:
        trial.shell.replies(when="gh pr edit 7*")
        trial.shell.replies(when=_IS_ANCESTOR)
        trial.shell.replies(when=_MERGE)

        assert trial.walk(merge_base, work) == goto(
            take_pass, work.graded(unchanged=True)
        )

    @staticmethod
    def test_a_conflict_goes_to_the_resolver(trial: Trial, work: Work) -> None:
        trial.shell.replies(when="gh pr edit 7*")
        trial.shell.replies(when=_IS_ANCESTOR, exit_code=1)
        trial.shell.replies(when=_MERGE, exit_code=1, stdout="CONFLICT in a.py")

        assert trial.walk(merge_base, work) == goto(
            resolve_conflicts, work.merging_on("git merge failed: CONFLICT in a.py")
        )

    @staticmethod
    def test_a_checkpoint_that_will_not_go_on_is_said_and_survived(
        trial: Trial, work: Work
    ) -> None:
        trial.shell.replies(when="gh pr edit 7*", exit_code=1, stderr="no label")
        trial.shell.replies(when=_IS_ANCESTOR, exit_code=1)
        trial.shell.replies(when=_MERGE)

        assert trial.walk(merge_base, work) == goto(
            take_pass, work.graded(unchanged=False)
        )
        assert "could not mark v:refresh:started" in trial.deltas[0]


class TestResolveConflicts:
    @staticmethod
    def test_hands_the_files_to_a_resolver(trial: Trial, work: Work) -> None:
        trial.shell.replies(when=_UNMERGED, stdout="src/thing.py\n")
        trial.coding.replies("resolved")

        transition = trial.walk(resolve_conflicts, work.merging_on("git merge failed"))

        assert transition == goto(
            resolve_conflicts, work.merging_on("").charged(resolve_conflicts.name)
        )
        assert "Merging main into feature" in trial.coding.prompts[0]
        assert "src/thing.py" in trial.coding.prompts[0]
        assert trial.coding.calls[0].resume is None
        assert trial.coding.calls[0].focus_options is not None
        assert "Bash(git add:*)" in str(trial.coding.calls[0].focus_options)

    @staticmethod
    def test_an_attended_cast_asks_before_a_resolver_is_spent(
        trial: Trial, work: Work
    ) -> None:
        trial.shell.replies(when=_UNMERGED, stdout="src/thing.py\n")
        trial.decide.answers(answer=False, when="resolve the conflicts*")
        attended = work.but(run=work.run.model_copy(update={"attended": True}))

        assert trial.walk(resolve_conflicts, attended.merging_on("")) == goto(
            stand_down,
            attended.merging_on("").stopped_by("the merge conflicts were not resolved"),
        )
        assert trial.decide.prompts == ["resolve the conflicts on feature (attempt 1)?"]
        assert not trial.coding.prompts

    @staticmethod
    def test_an_index_that_cannot_be_read_is_set_aside(
        trial: Trial, work: Work
    ) -> None:
        trial.shell.replies(when=_UNMERGED, exit_code=128, stderr="lock")
        merging = work.merging_on("")

        assert trial.walk(resolve_conflicts, merging) == goto(
            set_aside, merging.but(note="could not read the index: lock")
        )

    @staticmethod
    def test_nothing_conflicted_and_nothing_tried_is_not_a_conflict(
        trial: Trial, work: Work
    ) -> None:
        trial.shell.replies(when=_UNMERGED)

        assert trial.walk(
            resolve_conflicts, work.merging_on("git merge failed: lock")
        ) == goto(
            set_aside,
            work.merging_on("git merge failed: lock").but(
                note="no conflicts: git merge failed: lock"
            ),
        )
        assert not trial.coding.prompts

    @staticmethod
    def test_a_clean_index_after_a_round_goes_on(trial: Trial, work: Work) -> None:
        trial.shell.replies(when=_UNMERGED)
        charged = work.merging_on("").charged(resolve_conflicts.name)

        assert trial.walk(resolve_conflicts, charged) == goto(
            take_pass, work.merging_on("")
        )

    @staticmethod
    def test_a_spent_budget_stands_the_branch_down(trial: Trial, work: Work) -> None:
        trial.shell.replies(when=_UNMERGED, stdout="src/thing.py\n")
        spent = work.merging_on("").but(budgets={resolve_conflicts.name: 3})

        assert trial.walk(resolve_conflicts, spent) == goto(
            stand_down, spent.stopped_by("the merge conflicts were not resolved")
        )
        assert not trial.coding.prompts

    @staticmethod
    def test_an_agent_that_dies_ends_the_run(trial: Trial, work: Work) -> None:
        falling()
        trial.shell.replies(when=_UNMERGED, stdout="src/thing.py\n")

        assert trial.walk(resolve_conflicts, work.merging_on("")) == goto(
            report, work.merging_on("").abandoned("the agent stopped mid-flight: boom")
        )
