"""The merge task: the gate repaired, the merge committed, the work pushed."""

import pytest
from vekna.trial import Trial

from cabinet.gates.ritual.vekna.heal import finish_merge, gate_check, push_work, tend
from cabinet.pacts.heal import (
    Chart,
    FinishMerge,
    FinishPr,
    GateCheck,
    MergeBase,
    PushWork,
    QualityReview,
    SetAside,
    StandDown,
    Tend,
)
from cabinet.pacts.healing import TASKS, Task, Work
from cabinet.specs import BUDGET
from tests.conftest import commit
from tests.integration.rituals.falling import falling

_GATE = "CI=1 mise run pr-fix"
_MERGE_COMMIT = commit("chore: merge main and fix the gates")
_PUSH = "git push origin feature"


class TestTend:
    @staticmethod
    def test_the_next_task_goes_first(trial: Trial, work: Work) -> None:
        both = work.but(todos=["merge", "review"])

        assert trial.walk(tend, both.to(Tend)) == work.but(todos=["review"]).to(
            MergeBase
        )

    @staticmethod
    def test_the_review_is_a_task(trial: Trial, work: Work) -> None:
        reviewing = work.but(todos=["review"])

        assert trial.walk(tend, reviewing.to(Tend)) == work.to(QualityReview)

    @staticmethod
    @pytest.mark.parametrize("task", TASKS)
    def test_every_task_has_a_first_step(trial: Trial, work: Work, task: Task) -> None:
        transition = trial.walk(tend, work.but(todos=[task]).to(Tend))

        assert isinstance(transition, Work)
        assert transition.todos == []

    @staticmethod
    def test_a_branch_with_nothing_left_is_finished(trial: Trial, work: Work) -> None:
        assert trial.walk(tend, work.to(Tend)) == work.to(FinishPr)

    # The review's comments anchor to code, and the forge only has what was
    # pushed.
    @staticmethod
    def test_what_was_committed_is_pushed_before_the_review(
        trial: Trial, work: Work
    ) -> None:
        merged = work.merged().but(todos=["review"])

        assert trial.walk(tend, merged.to(Tend)) == merged.to(PushWork)

    @staticmethod
    def test_what_was_committed_is_pushed_before_the_branch_is_left(
        trial: Trial, work: Work
    ) -> None:
        merged = work.merged()

        assert trial.walk(tend, merged.to(Tend)) == merged.to(PushWork)


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
        assert "You have a shell" in prompt
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
    def test_a_verdict_the_cast_gave_up_on_is_not_paid_for_twice(
        trial: Trial, work: Work
    ) -> None:
        trial.shell.replies(when=_GATE, exit_code=1, stdout="1 failed in 2s")
        seen = work.but(run=work.run.but(seen=["1 failed in 9s"]))

        assert trial.walk(gate_check, seen.to(GateCheck)) == seen.stopped_by(
            "`mise run pr-fix` is red as it already was:\n1 failed in 2s"
        ).to(StandDown)

    @staticmethod
    def test_an_agent_that_dies_ends_the_cast(trial: Trial, work: Work) -> None:
        falling()
        trial.shell.replies(when=_GATE, exit_code=1, stdout="1 failed")

        assert trial.walk(gate_check, work.to(GateCheck)) == work.abandoned(
            "the agent stopped mid-flight: boom"
        ).to(Chart)

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
    def test_a_clean_merge_commits_the_repairs(trial: Trial, work: Work) -> None:
        trial.shell.replies(when="git add -A*")

        assert trial.walk(finish_merge, work.to(FinishMerge)) == work.merged().to(Tend)
        assert trial.shell.commands == [_MERGE_COMMIT]

    @staticmethod
    def test_an_open_merge_is_continued_first(trial: Trial, work: Work) -> None:
        trial.shell.replies(when="if git rev-parse*")
        trial.shell.replies(when="git add -A*")
        merging = work.merging_on("")

        assert trial.walk(finish_merge, merging.to(FinishMerge)) == merging.merged().to(
            Tend
        )
        assert trial.shell.commands[0].startswith("if git rev-parse")

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


class TestPushWork:
    @staticmethod
    def test_pushes_and_tends_on(trial: Trial, work: Work) -> None:
        trial.shell.replies(when=_PUSH)

        assert trial.walk(push_work, work.merged().to(PushWork)) == work.to(Tend)
        assert trial.shell.commands == [_PUSH]

    @staticmethod
    def test_a_push_that_fails_is_noted_and_survived(trial: Trial, work: Work) -> None:
        trial.shell.replies(when=_PUSH, exit_code=1, stderr="rejected")

        assert trial.walk(push_work, work.merged().to(PushWork)) == work.but(
            note="could not push feature: rejected"
        ).to(Tend)
