"""Taking a branch: standing on it, merging the base in."""

from vekna.trial import Trial

from cabinet.gates.ritual.vekna.heal import (
    check_clean,
    merge_base,
    resolve_conflicts,
    sync_branch,
)
from cabinet.pacts.heal import (
    Chart,
    CheckClean,
    GateCheck,
    MergeBase,
    ResolveConflicts,
    SetAside,
    SkipPr,
    StandDown,
    SyncBranch,
    Tend,
)
from cabinet.pacts.healing import Work
from tests.conftest import STATUS
from tests.integration.rituals.falling import falling

_UNMERGED = "git diff --name-only --diff-filter=U"
_IS_ANCESTOR = "git merge-base --is-ancestor main HEAD"
_MERGE = "git merge --no-edit main"


class TestCheckClean:
    @staticmethod
    def test_a_clean_tree_goes_on(trial: Trial, work: Work) -> None:
        trial.shell.replies(when=STATUS)

        assert trial.walk(check_clean, work.to(CheckClean)) == work.to(SyncBranch)

    @staticmethod
    def test_a_dirty_tree_ends_the_cast(trial: Trial, work: Work) -> None:
        trial.shell.replies(when=STATUS, stdout=" M a.py\n")

        transition = trial.walk(check_clean, work.to(CheckClean))

        assert transition == work.abandoned("the worktree is not clean:\nM a.py").to(
            Chart
        )

    @staticmethod
    def test_a_status_that_fails_ends_the_cast(trial: Trial, work: Work) -> None:
        trial.shell.replies(when=STATUS, exit_code=128, stderr="not a repo")

        assert trial.walk(check_clean, work.to(CheckClean)) == work.abandoned(
            "git status failed: not a repo"
        ).to(Chart)


class TestSyncBranch:
    @staticmethod
    def test_updates_the_base_then_stands_on_the_branch(
        trial: Trial, work: Work
    ) -> None:
        trial.shell.replies(when="git fetch*")
        trial.shell.replies(when="git checkout feature")
        trial.shell.replies(when="git merge --ff-only*")

        assert trial.walk(sync_branch, work.to(SyncBranch)) == work.to(Tend)
        assert trial.shell.commands == [
            (
                "git fetch --prune origin && git checkout main"
                " && git pull --ff-only origin main"
            ),
            "git checkout feature",
            "git merge --ff-only origin/feature",
        ]

    @staticmethod
    def test_a_base_that_will_not_update_ends_the_cast(
        trial: Trial, work: Work
    ) -> None:
        trial.shell.replies(when="git fetch*", exit_code=1, stderr="no network")

        assert trial.walk(sync_branch, work.to(SyncBranch)) == work.abandoned(
            "could not update main: no network"
        ).to(Chart)

    @staticmethod
    def test_a_checkout_that_will_not_go_through_skips_the_branch(
        trial: Trial, work: Work
    ) -> None:
        trial.shell.replies(when="git fetch*")
        trial.shell.replies(when="git checkout feature", exit_code=1, stderr="busy")

        assert trial.walk(sync_branch, work.to(SyncBranch)) == work.but(
            note="could not take feature: busy"
        ).to(SkipPr)

    @staticmethod
    def test_a_diverged_branch_is_set_aside(trial: Trial, work: Work) -> None:
        trial.shell.replies(when="git fetch*")
        trial.shell.replies(when="git checkout feature")
        trial.shell.replies(when="git merge --ff-only*", exit_code=1, stderr="diverged")

        assert trial.walk(sync_branch, work.to(SyncBranch)) == work.but(
            note="could not catch up with the remote: diverged"
        ).to(SetAside)


class TestMergeBase:
    @staticmethod
    def test_a_clean_merge_owes_the_gate(trial: Trial, work: Work) -> None:
        trial.shell.replies(when=_IS_ANCESTOR, exit_code=1)
        trial.shell.replies(when=_MERGE)

        assert trial.walk(merge_base, work.to(MergeBase)) == work.to(GateCheck)
        assert trial.shell.commands == [_IS_ANCESTOR, _MERGE]

    # The forge said the branch conflicts, and it no longer does: somebody
    # merged the base in since.
    @staticmethod
    def test_a_base_already_contained_is_nothing_to_merge(
        trial: Trial, work: Work
    ) -> None:
        trial.shell.replies(when=_IS_ANCESTOR)

        assert trial.walk(merge_base, work.to(MergeBase)) == work.but(
            note="main is already merged in"
        ).to(Tend)
        assert trial.shell.commands == [_IS_ANCESTOR]

    @staticmethod
    def test_a_conflict_goes_to_the_resolver(trial: Trial, work: Work) -> None:
        trial.shell.replies(when=_IS_ANCESTOR, exit_code=1)
        trial.shell.replies(when=_MERGE, exit_code=1, stdout="CONFLICT in a.py")

        assert trial.walk(merge_base, work.to(MergeBase)) == work.merging_on(
            "git merge failed: CONFLICT in a.py"
        ).to(ResolveConflicts)


class TestResolveConflicts:
    @staticmethod
    def test_hands_the_files_to_a_resolver(trial: Trial, work: Work) -> None:
        trial.shell.replies(when=_UNMERGED, stdout="src/thing.py\n")
        trial.coding.replies("resolved")

        transition = trial.walk(
            resolve_conflicts, work.merging_on("git merge failed").to(ResolveConflicts)
        )

        assert transition == work.merging_on("").charged(resolve_conflicts.name).to(
            ResolveConflicts
        )
        assert "Merging main into feature" in trial.coding.prompts[0]
        assert "src/thing.py" in trial.coding.prompts[0]
        assert "git add" in trial.coding.prompts[0]
        assert trial.coding.calls[0].resume is None

    @staticmethod
    def test_an_attended_cast_asks_before_a_resolver_is_spent(
        trial: Trial, work: Work
    ) -> None:
        trial.shell.replies(when=_UNMERGED, stdout="src/thing.py\n")
        trial.decide.answers(answer=False, when="resolve the conflicts*")
        attended = work.but(run=work.run.model_copy(update={"attended": True}))

        assert trial.walk(
            resolve_conflicts, attended.merging_on("").to(ResolveConflicts)
        ) == attended.merging_on("").stopped_by(
            "the merge conflicts were not resolved"
        ).to(
            StandDown
        )
        assert trial.decide.prompts == ["resolve the conflicts on feature (attempt 1)?"]
        assert not trial.coding.prompts

    @staticmethod
    def test_an_index_that_cannot_be_read_is_set_aside(
        trial: Trial, work: Work
    ) -> None:
        trial.shell.replies(when=_UNMERGED, exit_code=128, stderr="lock")
        merging = work.merging_on("")

        assert trial.walk(
            resolve_conflicts, merging.to(ResolveConflicts)
        ) == merging.but(note="could not read the index: lock").to(SetAside)

    @staticmethod
    def test_nothing_conflicted_and_nothing_tried_is_not_a_conflict(
        trial: Trial, work: Work
    ) -> None:
        trial.shell.replies(when=_UNMERGED)

        assert trial.walk(
            resolve_conflicts,
            work.merging_on("git merge failed: lock").to(ResolveConflicts),
        ) == work.merging_on("git merge failed: lock").but(
            note="no conflicts: git merge failed: lock"
        ).to(
            SetAside
        )
        assert not trial.coding.prompts

    @staticmethod
    def test_a_clean_index_after_a_round_goes_on(trial: Trial, work: Work) -> None:
        trial.shell.replies(when=_UNMERGED)
        charged = work.merging_on("").charged(resolve_conflicts.name)

        assert trial.walk(
            resolve_conflicts, charged.to(ResolveConflicts)
        ) == work.merging_on("").to(GateCheck)

    @staticmethod
    def test_a_spent_budget_stands_the_branch_down(trial: Trial, work: Work) -> None:
        trial.shell.replies(when=_UNMERGED, stdout="src/thing.py\n")
        spent = work.merging_on("").but(budgets={resolve_conflicts.name: 3})

        assert trial.walk(
            resolve_conflicts, spent.to(ResolveConflicts)
        ) == spent.stopped_by("the merge conflicts were not resolved").to(StandDown)
        assert not trial.coding.prompts

    @staticmethod
    def test_an_agent_that_dies_ends_the_cast(trial: Trial, work: Work) -> None:
        falling()
        trial.shell.replies(when=_UNMERGED, stdout="src/thing.py\n")

        assert trial.walk(
            resolve_conflicts, work.merging_on("").to(ResolveConflicts)
        ) == work.merging_on("").abandoned("the agent stopped mid-flight: boom").to(
            Chart
        )
