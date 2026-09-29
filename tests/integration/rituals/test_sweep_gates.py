"""The gates: where the fast pass and the slow one part."""

from vekna.trial import Trial

from cabinet.gates.ritual.vekna.sweep import (
    check_ci,
    close_gap,
    finish_merge,
    gate_check,
    push_work,
    take_pass,
)
from cabinet.pacts.pulls import Closed, Work
from cabinet.pacts.sweep import (
    CheckCi,
    CloseGap,
    FinishMerge,
    GateCheck,
    PushWork,
    QualityReview,
    Reporting,
    SetAside,
    StandDown,
    TakePass,
)
from cabinet.specs import BUDGET
from tests.conftest import board, commit
from tests.integration.rituals.falling import falling

_GATE = "CI=1 mise run pr-fix"
_COVERAGE = "CI=1 mise run diff-cover"
_FAST = "CI=1 mise run test:py:cov:diff"
_MERGE_COMMIT = commit("chore: merge main and fix the gates")
_TEST_COMMIT = commit("test: cover the lines this branch changes")
_PUSH = "git push origin feature"

_GREEN_BOARD = """{"total_count": 5, "check_runs": [
  {"name": "checks", "conclusion": "success"},
  {"name": "test", "conclusion": "success"},
  {"name": "test-postgres", "conclusion": "success"},
  {"name": "codecov/project", "conclusion": "success"},
  {"name": "codecov/patch", "conclusion": "success",
   "output": {"title": "100.00% of diff hit (target 96.00%)"}}]}"""
# Derived, so the patch title is provably the only difference.
_GAP_BOARD = _GREEN_BOARD.replace("100.00% of diff hit", "96.84% of diff hit")
_RED_BOARD = _GREEN_BOARD.replace(
    '"checks", "conclusion": "success"', '"checks", "conclusion": "failure"'
)

_MISSING = """Diff Coverage
Diff: main...HEAD
-------------
src/thing.py (80.0%): Missing lines 12-14
-------------
Total:   10 lines
Missing: 3 lines
-------------
"""
_CLEAN = _MISSING.replace("src/thing.py (80.0%): Missing lines 12-14\n", "").replace(
    "Missing: 3 lines", "Missing: 0 lines"
)


def _cover(work: Work) -> Work:
    return work.but(run=work.run.but(seen=[])).model_copy(
        update={"run": work.run.model_copy(update={"mode": "cover"})}
    )


class TestTakePass:
    @staticmethod
    def test_the_slow_pass_owes_no_gate(trial: Trial, work: Work) -> None:
        slow = _cover(work)

        assert trial.walk(take_pass, slow.to(TakePass)) == slow.to(FinishMerge)

    @staticmethod
    def test_an_unchanged_tree_ci_ran_green_skips_the_gate(
        trial: Trial, work: Work
    ) -> None:
        trial.shell.replies(when=board(), stdout=_GREEN_BOARD)
        unchanged = work.graded(unchanged=True)

        assert trial.walk(take_pass, unchanged.to(TakePass)) == unchanged.but(
            note="nothing to merge, and CI ran the gate green"
        ).to(FinishMerge)

    @staticmethod
    def test_a_red_gate_job_buys_the_gate(trial: Trial, work: Work) -> None:
        trial.shell.replies(when=board(), stdout=_RED_BOARD)
        unchanged = work.graded(unchanged=True)

        assert trial.walk(take_pass, unchanged.to(TakePass)) == unchanged.to(GateCheck)

    @staticmethod
    def test_a_board_the_forge_would_not_give_buys_the_gate(
        trial: Trial, work: Work
    ) -> None:
        trial.shell.replies(when=board(), exit_code=1)
        unchanged = work.graded(unchanged=True)

        assert trial.walk(take_pass, unchanged.to(TakePass)) == unchanged.to(GateCheck)

    @staticmethod
    def test_a_changed_tree_never_asks(trial: Trial, work: Work) -> None:
        assert trial.walk(take_pass, work.to(TakePass)) == work.to(GateCheck)
        assert not trial.shell.commands


def _attended(work: Work) -> Work:
    return work.but(run=work.run.model_copy(update={"attended": True}))


class TestGateCheck:
    @staticmethod
    def test_an_unattended_cast_asks_nobody(trial: Trial, work: Work) -> None:
        trial.shell.replies(when=_GATE, exit_code=1, stdout="1 failed")
        trial.coding.replies("fixed")

        trial.walk(gate_check, work.to(GateCheck))

        assert not trial.decide.prompts
        assert "permission_mode='dontAsk'" in str(trial.coding.calls[0].focus_options)

    @staticmethod
    def test_an_attended_cast_asks_before_each_repair(trial: Trial, work: Work) -> None:
        trial.shell.replies(when=_GATE, exit_code=1, stdout="1 failed")
        trial.decide.answers(answer=True, when="repair `mise run pr-fix`*")
        trial.coding.replies("fixed")
        attended = _attended(work).charged(gate_check.name)

        transition = trial.walk(gate_check, attended.to(GateCheck))

        assert transition == attended.but(gate="").charged(gate_check.name).to(
            GateCheck
        )
        assert trial.decide.prompts == [
            "repair `mise run pr-fix` on feature (attempt 2)?"
        ]
        assert "permission_mode='auto'" in str(trial.coding.calls[0].focus_options)

    @staticmethod
    def test_a_declined_repair_stands_the_branch_down(trial: Trial, work: Work) -> None:
        trial.shell.replies(when=_GATE, exit_code=1, stdout="1 failed")
        trial.decide.answers(answer=False, when="repair `mise run pr-fix`*")
        attended = _attended(work)

        assert trial.walk(gate_check, attended.to(GateCheck)) == attended.stopped_by(
            "`mise run pr-fix` was not tried again, as you decided:\n1 failed"
        ).but(run=attended.run.but(seen=["1 failed"])).to(StandDown)
        assert not trial.coding.prompts

    @staticmethod
    def test_a_green_gate_lands(trial: Trial, work: Work) -> None:
        trial.shell.replies(when=_GATE)
        spent = work.but(budgets={gate_check.name: 1})

        assert trial.walk(gate_check, spent.to(GateCheck)) == work.to(FinishMerge)
        assert trial.shell.commands == [_GATE]

    @staticmethod
    def test_a_green_narrow_task_spends_the_gate(trial: Trial, work: Work) -> None:
        trial.shell.replies(when="CI=1 mise run lint:mypy")
        narrowed = work.but(gate="mise run lint:mypy")

        assert trial.walk(gate_check, narrowed.to(GateCheck)) == work.to(GateCheck)

    @staticmethod
    def test_a_red_gate_is_handed_to_a_writer(trial: Trial, work: Work) -> None:
        trial.shell.replies(
            when=_GATE,
            exit_code=1,
            stdout="E501 line too long\n1 failed",
            stderr="[lint:ruff] ERROR task failed\n[pr-fix] ERROR task failed",
        )
        trial.coding.replies("fixed")

        transition = trial.walk(gate_check, work.to(GateCheck))

        assert transition == work.but(gate="mise run lint:ruff").charged(
            gate_check.name
        ).to(GateCheck)
        prompt = trial.coding.prompts[0]
        assert prompt.startswith("`mise run pr-fix` is this project's gate")
        assert "E501 line too long\n1 failed" in prompt
        assert "do not disable a lint rule" in prompt
        assert "You cannot run the project's tasks" in prompt
        assert trial.coding.calls[0].resume is None

    @staticmethod
    def test_a_spent_budget_stands_the_branch_down_and_remembers(
        trial: Trial, work: Work
    ) -> None:
        trial.shell.replies(when=_GATE, exit_code=1, stdout="1 failed")
        spent = work.but(budgets={gate_check.name: 3})

        transition = trial.walk(gate_check, spent.to(GateCheck))

        assert transition == spent.stopped_by(
            "`mise run pr-fix` is still red:\n1 failed"
        ).but(run=work.run.but(seen=["1 failed"])).to(StandDown)
        assert not trial.coding.prompts

    @staticmethod
    def test_a_verdict_the_night_gave_up_on_is_not_paid_for_twice(
        trial: Trial, work: Work
    ) -> None:
        trial.shell.replies(when=_GATE, exit_code=1, stdout="1 failed in 2s")
        seen = work.but(run=work.run.but(seen=["1 failed in 9s"]))

        assert trial.walk(gate_check, seen.to(GateCheck)) == seen.stopped_by(
            "`mise run pr-fix` is red as it already was:\n1 failed in 2s"
        ).to(StandDown)

    @staticmethod
    def test_an_agent_that_dies_ends_the_run(trial: Trial, work: Work) -> None:
        falling()
        trial.shell.replies(when=_GATE, exit_code=1, stdout="1 failed")

        assert trial.walk(gate_check, work.to(GateCheck)) == work.abandoned(
            "the agent stopped mid-flight: boom"
        ).to(Reporting)

    @staticmethod
    def test_the_agent_reads_a_trimmed_log(trial: Trial, work: Work) -> None:
        passed = "\n".join(f"tests/test_{index}.py PASSED" for index in range(4000))
        trial.shell.replies(when=_GATE, exit_code=1, stdout=f"{passed}\n1 failed")
        trial.coding.replies("fixed")

        trial.walk(gate_check, work.to(GateCheck))

        prompt = trial.coding.prompts[0]
        assert "1 failed" in prompt
        assert "tests/test_0.py PASSED" not in prompt
        assert len(prompt) < BUDGET * 2


class TestFinishMerge:
    @staticmethod
    def test_a_clean_merge_commits_the_repairs_and_pushes(
        trial: Trial, work: Work
    ) -> None:
        trial.shell.replies(when="git add -A*")

        assert trial.walk(finish_merge, work.to(FinishMerge)) == work.to(PushWork)
        assert trial.shell.commands == [_MERGE_COMMIT]

    @staticmethod
    def test_an_open_merge_is_continued_first(trial: Trial, work: Work) -> None:
        trial.shell.replies(when="if git rev-parse*")
        trial.shell.replies(when="git add -A*")
        merging = work.merging_on("")

        assert trial.walk(finish_merge, merging.to(FinishMerge)) == work.to(PushWork)
        assert trial.shell.commands[0].startswith("if git rev-parse")

    @staticmethod
    def test_the_slow_pass_asks_ci_next(trial: Trial, work: Work) -> None:
        trial.shell.replies(when="git add -A*")
        slow = _cover(work)

        assert trial.walk(finish_merge, slow.to(FinishMerge)) == slow.to(CheckCi)

    @staticmethod
    def test_a_merge_that_will_not_close_is_set_aside(trial: Trial, work: Work) -> None:
        trial.shell.replies(when="if git rev-parse*", exit_code=1, stderr="unmerged")
        merging = work.merging_on("")

        assert trial.walk(finish_merge, merging.to(FinishMerge)) == merging.but(
            note="could not finish the merge: unmerged"
        ).to(SetAside)

    @staticmethod
    def test_a_commit_that_fails_is_set_aside(trial: Trial, work: Work) -> None:
        trial.shell.replies(when="git add -A*", exit_code=1, stderr="gpg failed")

        assert trial.walk(finish_merge, work.to(FinishMerge)) == work.but(
            note="could not commit the merge: could not commit: gpg failed"
        ).to(SetAside)


class TestCheckCi:
    @staticmethod
    def test_a_green_board_skips_the_hour(trial: Trial, work: Work) -> None:
        trial.shell.replies(when=board(), stdout=_GREEN_BOARD)

        assert trial.walk(check_ci, work.to(CheckCi)) == work.but(
            note="coverage and the suite are green on CI"
        ).to(PushWork)

    @staticmethod
    def test_a_patch_with_a_gap_buys_the_hour(trial: Trial, work: Work) -> None:
        trial.shell.replies(when=board(), stdout=_GAP_BOARD)

        assert trial.walk(check_ci, work.to(CheckCi)) == work.to(CloseGap)

    @staticmethod
    def test_a_board_the_forge_would_not_give_buys_the_hour(
        trial: Trial, work: Work
    ) -> None:
        trial.shell.replies(when=board(), exit_code=1)

        assert trial.walk(check_ci, work.to(CheckCi)) == work.to(CloseGap)


class TestCover:
    @staticmethod
    def test_a_declined_round_stands_the_branch_down(trial: Trial, work: Work) -> None:
        trial.shell.replies(when=_COVERAGE, stdout=_MISSING)
        trial.decide.answers(answer=False, when="work on `mise run diff-cover`*")
        attended = _attended(work)

        assert trial.walk(close_gap, attended.to(CloseGap)) == attended.stopped_by(
            "`mise run diff-cover` was not tried again, as you decided:\n"
            + _MISSING.rstrip("\n")
        ).to(StandDown)
        assert trial.decide.prompts == [
            "work on `mise run diff-cover` on feature (attempt 1)?"
        ]

    @staticmethod
    def test_a_clean_first_measurement_commits_nothing(
        trial: Trial, work: Work
    ) -> None:
        trial.shell.replies(when=_COVERAGE, stdout=_CLEAN)

        assert trial.walk(close_gap, work.to(CloseGap)) == work.to(PushWork)
        assert trial.shell.commands == [_COVERAGE]

    @staticmethod
    def test_a_clean_measurement_after_a_round_commits_the_tests(
        trial: Trial, work: Work
    ) -> None:
        trial.shell.replies(when=_COVERAGE, stdout=_CLEAN)
        trial.shell.replies(when="git add -A*")
        charged = work.but(budgets={close_gap.name: 1})

        assert trial.walk(close_gap, charged.to(CloseGap)) == work.to(PushWork)
        assert trial.shell.commands == [_COVERAGE, _TEST_COMMIT]

    @staticmethod
    def test_a_clean_fast_measurement_spends_the_full_one(
        trial: Trial, work: Work
    ) -> None:
        trial.shell.replies(when=_FAST, stdout=_CLEAN)
        fast = work.but(gate="mise run test:py:cov:diff")

        assert trial.walk(close_gap, fast.to(CloseGap)) == work.to(CloseGap)

    @staticmethod
    def test_missing_lines_are_handed_to_a_writer(trial: Trial, work: Work) -> None:
        trial.shell.replies(when=_COVERAGE, stdout=f"tests PASSED\n{_MISSING}")
        trial.coding.replies("wrote a test")

        transition = trial.walk(close_gap, work.to(CloseGap))

        assert transition == work.but(gate="mise run test:py:cov:diff").charged(
            close_gap.name
        ).to(CloseGap)
        prompt = trial.coding.prompts[0]
        assert _MISSING in prompt
        assert "tests PASSED" not in prompt
        assert "leaves the slow suites out" not in prompt

    @staticmethod
    def test_the_fast_measurement_says_what_it_cannot_see(
        trial: Trial, work: Work
    ) -> None:
        trial.shell.replies(when=_FAST, stdout=_MISSING)
        trial.coding.replies("wrote a test")
        fast = work.but(gate="mise run test:py:cov:diff").charged(close_gap.name)

        trial.walk(close_gap, fast.to(CloseGap))

        assert "leaves the slow suites out" in trial.coding.prompts[0]

    @staticmethod
    def test_a_red_suite_is_repaired_against_the_task_that_broke(
        trial: Trial, work: Work
    ) -> None:
        trial.shell.replies(
            when=_COVERAGE,
            exit_code=1,
            stdout="1 failed",
            stderr="[test:unit] ERROR task failed",
        )
        trial.coding.replies("fixed")

        transition = trial.walk(close_gap, work.to(CloseGap))

        assert transition == work.but(gate="mise run test:unit").charged(
            close_gap.name
        ).to(CloseGap)
        assert trial.coding.prompts[0].startswith(
            "`mise run diff-cover` is this project's gate"
        )

    @staticmethod
    def test_a_red_suite_that_stays_red_is_remembered(trial: Trial, work: Work) -> None:
        trial.shell.replies(when=_COVERAGE, exit_code=1, stdout="1 failed")
        spent = work.but(budgets={close_gap.name: 3})

        assert trial.walk(close_gap, spent.to(CloseGap)) == spent.stopped_by(
            "`mise run diff-cover` is still red:\n1 failed"
        ).but(run=work.run.but(seen=["1 failed"])).to(StandDown)

    @staticmethod
    def test_missing_lines_that_stay_missing_are_not_remembered(
        trial: Trial, work: Work
    ) -> None:
        trial.shell.replies(when=_COVERAGE, stdout=_MISSING)
        spent = work.but(budgets={close_gap.name: 3})

        transition = trial.walk(close_gap, spent.to(CloseGap))

        assert transition == spent.stopped_by(
            "`mise run diff-cover` still reports missing lines:\n"
            + _MISSING.rstrip("\n")
        ).to(StandDown)

    @staticmethod
    def test_a_suite_broken_the_way_last_branch_was_stands_down(
        trial: Trial, work: Work
    ) -> None:
        trial.shell.replies(when=_COVERAGE, exit_code=1, stdout="1 failed in 2s")
        seen = work.but(run=work.run.but(seen=["1 failed in 9s"]))

        assert trial.walk(close_gap, seen.to(CloseGap)) == seen.stopped_by(
            "`mise run diff-cover` is red as it already was:\n1 failed in 2s"
        ).to(StandDown)
        assert not trial.coding.prompts

    @staticmethod
    def test_a_test_commit_that_fails_is_set_aside(trial: Trial, work: Work) -> None:
        trial.shell.replies(when=_COVERAGE, stdout=_CLEAN)
        trial.shell.replies(when="git add -A*", exit_code=1, stderr="gpg failed")
        charged = work.but(budgets={close_gap.name: 1})

        assert trial.walk(close_gap, charged.to(CloseGap)) == charged.but(
            note="could not commit the tests: could not commit: gpg failed"
        ).to(SetAside)

    @staticmethod
    def test_an_agent_that_dies_ends_the_run(trial: Trial, work: Work) -> None:
        falling()
        trial.shell.replies(when=_COVERAGE, stdout=_MISSING)

        assert trial.walk(close_gap, work.to(CloseGap)) == work.abandoned(
            "the agent stopped mid-flight: boom"
        ).to(Reporting)


class TestPushWork:
    @staticmethod
    def test_the_fast_pass_goes_on_to_the_review(trial: Trial, work: Work) -> None:
        trial.shell.replies(when=_PUSH)

        assert trial.walk(push_work, work.to(PushWork)) == work.to(QualityReview)

    @staticmethod
    def test_the_slow_pass_is_done(trial: Trial, work: Work) -> None:
        trial.shell.replies(when=_PUSH)
        slow = _cover(work)

        assert trial.walk(push_work, slow.to(PushWork)) == Closed(
            work=slow, outcome="green"
        )

    @staticmethod
    def test_a_push_that_fails_is_noted_and_survived(trial: Trial, work: Work) -> None:
        trial.shell.replies(when=_PUSH, exit_code=1, stderr="rejected")

        assert trial.walk(push_work, work.to(PushWork)) == work.but(
            note="could not push feature: rejected"
        ).to(QualityReview)

    @staticmethod
    def test_a_blocked_branch_is_closed_blocked(trial: Trial, work: Work) -> None:
        trial.shell.replies(when=_PUSH)
        blocked = _cover(work).standing_down("")

        assert trial.walk(push_work, blocked.to(PushWork)) == Closed(
            work=blocked, outcome="blocked"
        )
