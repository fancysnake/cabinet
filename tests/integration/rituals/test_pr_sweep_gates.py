"""The gates: where the fast pass and the slow one part."""

from typing import TYPE_CHECKING

from vekna.lexicon import goto

from cabinet.gates.ritual.vekna.pr_sweep import (
    check_ci,
    cover,
    finish_merge,
    finish_pr,
    gate_check,
    push_work,
    quality_review,
    report,
    set_aside,
    stand_down,
    take_pass,
)
from cabinet.pacts.pulls import Closed, Work
from cabinet.specs import BUDGET
from tests.conftest import board, commit
from tests.integration.rituals.falling import falling

if TYPE_CHECKING:
    from vekna.trial import Trial

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

        assert trial.walk(take_pass, slow) == goto(finish_merge, slow)

    @staticmethod
    def test_an_unchanged_tree_ci_ran_green_skips_the_gate(
        trial: Trial, work: Work
    ) -> None:
        trial.shell.replies(when=board(), stdout=_GREEN_BOARD)
        unchanged = work.graded(unchanged=True)

        assert trial.walk(take_pass, unchanged) == goto(
            finish_merge,
            unchanged.but(note="nothing to merge, and CI ran the gate green"),
        )

    @staticmethod
    def test_a_red_gate_job_buys_the_gate(trial: Trial, work: Work) -> None:
        trial.shell.replies(when=board(), stdout=_RED_BOARD)
        unchanged = work.graded(unchanged=True)

        assert trial.walk(take_pass, unchanged) == goto(gate_check, unchanged)

    @staticmethod
    def test_a_board_the_forge_would_not_give_buys_the_gate(
        trial: Trial, work: Work
    ) -> None:
        trial.shell.replies(when=board(), exit_code=1)
        unchanged = work.graded(unchanged=True)

        assert trial.walk(take_pass, unchanged) == goto(gate_check, unchanged)

    @staticmethod
    def test_a_changed_tree_never_asks(trial: Trial, work: Work) -> None:
        assert trial.walk(take_pass, work) == goto(gate_check, work)
        assert not trial.shell.commands


class TestGateCheck:
    @staticmethod
    def test_a_green_gate_lands(trial: Trial, work: Work) -> None:
        trial.shell.replies(when=_GATE)
        spent = work.but(budgets={gate_check.name: 1})

        assert trial.walk(gate_check, spent) == goto(finish_merge, work)
        assert trial.shell.commands == [_GATE]

    @staticmethod
    def test_a_green_narrow_task_spends_the_gate(trial: Trial, work: Work) -> None:
        trial.shell.replies(when="CI=1 mise run lint:mypy")
        narrowed = work.but(gate="mise run lint:mypy")

        assert trial.walk(gate_check, narrowed) == goto(gate_check, work)

    @staticmethod
    def test_a_red_gate_is_handed_to_a_writer(trial: Trial, work: Work) -> None:
        trial.shell.replies(
            when=_GATE,
            exit_code=1,
            stdout="E501 line too long\n1 failed",
            stderr="[lint:ruff] ERROR task failed\n[pr-fix] ERROR task failed",
        )
        trial.coding.replies("fixed")

        transition = trial.walk(gate_check, work)

        assert transition == goto(
            gate_check, work.but(gate="mise run lint:ruff").charged(gate_check.name)
        )
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

        transition = trial.walk(gate_check, spent)

        assert transition == goto(
            stand_down,
            spent.stopped_by("`mise run pr-fix` is still red:\n1 failed").but(
                run=work.run.but(seen=["1 failed"])
            ),
        )
        assert not trial.coding.prompts

    @staticmethod
    def test_a_verdict_the_night_gave_up_on_is_not_paid_for_twice(
        trial: Trial, work: Work
    ) -> None:
        trial.shell.replies(when=_GATE, exit_code=1, stdout="1 failed in 2s")
        seen = work.but(run=work.run.but(seen=["1 failed in 9s"]))

        assert trial.walk(gate_check, seen) == goto(
            stand_down,
            seen.stopped_by(
                "`mise run pr-fix` is red as it already was:\n1 failed in 2s"
            ),
        )

    @staticmethod
    def test_an_agent_that_dies_ends_the_run(trial: Trial, work: Work) -> None:
        falling()
        trial.shell.replies(when=_GATE, exit_code=1, stdout="1 failed")

        assert trial.walk(gate_check, work) == goto(
            report, work.abandoned("the agent stopped mid-flight: boom")
        )

    @staticmethod
    def test_the_agent_reads_a_trimmed_log(trial: Trial, work: Work) -> None:
        passed = "\n".join(f"tests/test_{index}.py PASSED" for index in range(4000))
        trial.shell.replies(when=_GATE, exit_code=1, stdout=f"{passed}\n1 failed")
        trial.coding.replies("fixed")

        trial.walk(gate_check, work)

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

        assert trial.walk(finish_merge, work) == goto(push_work, work)
        assert trial.shell.commands == [_MERGE_COMMIT]

    @staticmethod
    def test_an_open_merge_is_continued_first(trial: Trial, work: Work) -> None:
        trial.shell.replies(when="if git rev-parse*")
        trial.shell.replies(when="git add -A*")
        merging = work.merging_on("")

        assert trial.walk(finish_merge, merging) == goto(push_work, work)
        assert trial.shell.commands[0].startswith("if git rev-parse")

    @staticmethod
    def test_the_slow_pass_asks_ci_next(trial: Trial, work: Work) -> None:
        trial.shell.replies(when="git add -A*")
        slow = _cover(work)

        assert trial.walk(finish_merge, slow) == goto(check_ci, slow)

    @staticmethod
    def test_a_merge_that_will_not_close_is_set_aside(trial: Trial, work: Work) -> None:
        trial.shell.replies(when="if git rev-parse*", exit_code=1, stderr="unmerged")
        merging = work.merging_on("")

        assert trial.walk(finish_merge, merging) == goto(
            set_aside, merging.but(note="could not finish the merge: unmerged")
        )

    @staticmethod
    def test_a_commit_that_fails_is_set_aside(trial: Trial, work: Work) -> None:
        trial.shell.replies(when="git add -A*", exit_code=1, stderr="gpg failed")

        assert trial.walk(finish_merge, work) == goto(
            set_aside,
            work.but(note="could not commit the merge: could not commit: gpg failed"),
        )


class TestCheckCi:
    @staticmethod
    def test_a_green_board_skips_the_hour(trial: Trial, work: Work) -> None:
        trial.shell.replies(when=board(), stdout=_GREEN_BOARD)

        assert trial.walk(check_ci, work) == goto(
            push_work, work.but(note="coverage and the suite are green on CI")
        )

    @staticmethod
    def test_a_patch_with_a_gap_buys_the_hour(trial: Trial, work: Work) -> None:
        trial.shell.replies(when=board(), stdout=_GAP_BOARD)

        assert trial.walk(check_ci, work) == goto(cover, work)

    @staticmethod
    def test_a_board_the_forge_would_not_give_buys_the_hour(
        trial: Trial, work: Work
    ) -> None:
        trial.shell.replies(when=board(), exit_code=1)

        assert trial.walk(check_ci, work) == goto(cover, work)


class TestCover:
    @staticmethod
    def test_a_clean_first_measurement_commits_nothing(
        trial: Trial, work: Work
    ) -> None:
        trial.shell.replies(when=_COVERAGE, stdout=_CLEAN)

        assert trial.walk(cover, work) == goto(push_work, work)
        assert trial.shell.commands == [_COVERAGE]

    @staticmethod
    def test_a_clean_measurement_after_a_round_commits_the_tests(
        trial: Trial, work: Work
    ) -> None:
        trial.shell.replies(when=_COVERAGE, stdout=_CLEAN)
        trial.shell.replies(when="git add -A*")
        charged = work.but(budgets={cover.name: 1})

        assert trial.walk(cover, charged) == goto(push_work, work)
        assert trial.shell.commands == [_COVERAGE, _TEST_COMMIT]

    @staticmethod
    def test_a_clean_fast_measurement_spends_the_full_one(
        trial: Trial, work: Work
    ) -> None:
        trial.shell.replies(when=_FAST, stdout=_CLEAN)
        fast = work.but(gate="mise run test:py:cov:diff")

        assert trial.walk(cover, fast) == goto(cover, work)

    @staticmethod
    def test_missing_lines_are_handed_to_a_writer(trial: Trial, work: Work) -> None:
        trial.shell.replies(when=_COVERAGE, stdout=f"tests PASSED\n{_MISSING}")
        trial.coding.replies("wrote a test")

        transition = trial.walk(cover, work)

        assert transition == goto(
            cover, work.but(gate="mise run test:py:cov:diff").charged(cover.name)
        )
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
        fast = work.but(gate="mise run test:py:cov:diff").charged(cover.name)

        trial.walk(cover, fast)

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

        transition = trial.walk(cover, work)

        assert transition == goto(
            cover, work.but(gate="mise run test:unit").charged(cover.name)
        )
        assert trial.coding.prompts[0].startswith(
            "`mise run diff-cover` is this project's gate"
        )

    @staticmethod
    def test_a_red_suite_that_stays_red_is_remembered(trial: Trial, work: Work) -> None:
        trial.shell.replies(when=_COVERAGE, exit_code=1, stdout="1 failed")
        spent = work.but(budgets={cover.name: 3})

        assert trial.walk(cover, spent) == goto(
            stand_down,
            spent.stopped_by("`mise run diff-cover` is still red:\n1 failed").but(
                run=work.run.but(seen=["1 failed"])
            ),
        )

    @staticmethod
    def test_missing_lines_that_stay_missing_are_not_remembered(
        trial: Trial, work: Work
    ) -> None:
        trial.shell.replies(when=_COVERAGE, stdout=_MISSING)
        spent = work.but(budgets={cover.name: 3})

        transition = trial.walk(cover, spent)

        assert transition == goto(
            stand_down,
            spent.stopped_by(
                "`mise run diff-cover` still reports missing lines:\n"
                + _MISSING.rstrip("\n")
            ),
        )

    @staticmethod
    def test_a_suite_broken_the_way_last_branch_was_stands_down(
        trial: Trial, work: Work
    ) -> None:
        trial.shell.replies(when=_COVERAGE, exit_code=1, stdout="1 failed in 2s")
        seen = work.but(run=work.run.but(seen=["1 failed in 9s"]))

        assert trial.walk(cover, seen) == goto(
            stand_down,
            seen.stopped_by(
                "`mise run diff-cover` failed as it already did:\n1 failed in 2s"
            ),
        )
        assert not trial.coding.prompts

    @staticmethod
    def test_a_test_commit_that_fails_is_set_aside(trial: Trial, work: Work) -> None:
        trial.shell.replies(when=_COVERAGE, stdout=_CLEAN)
        trial.shell.replies(when="git add -A*", exit_code=1, stderr="gpg failed")
        charged = work.but(budgets={cover.name: 1})

        assert trial.walk(cover, charged) == goto(
            set_aside,
            charged.but(
                note="could not commit the tests: could not commit: gpg failed"
            ),
        )

    @staticmethod
    def test_an_agent_that_dies_ends_the_run(trial: Trial, work: Work) -> None:
        falling()
        trial.shell.replies(when=_COVERAGE, stdout=_MISSING)

        assert trial.walk(cover, work) == goto(
            report, work.abandoned("the agent stopped mid-flight: boom")
        )


class TestPushWork:
    @staticmethod
    def test_the_fast_pass_goes_on_to_the_review(trial: Trial, work: Work) -> None:
        trial.shell.replies(when=_PUSH)

        assert trial.walk(push_work, work) == goto(quality_review, work)

    @staticmethod
    def test_the_slow_pass_is_done(trial: Trial, work: Work) -> None:
        trial.shell.replies(when=_PUSH)
        slow = _cover(work)

        assert trial.walk(push_work, slow) == goto(
            finish_pr, Closed(work=slow, outcome="green")
        )

    @staticmethod
    def test_a_push_that_fails_is_noted_and_survived(trial: Trial, work: Work) -> None:
        trial.shell.replies(when=_PUSH, exit_code=1, stderr="rejected")

        assert trial.walk(push_work, work) == goto(
            quality_review, work.but(note="could not push feature: rejected")
        )

    @staticmethod
    def test_a_blocked_branch_is_closed_blocked(trial: Trial, work: Work) -> None:
        trial.shell.replies(when=_PUSH)
        blocked = _cover(work).standing_down("")

        assert trial.walk(push_work, blocked) == goto(
            finish_pr, Closed(work=blocked, outcome="blocked")
        )
