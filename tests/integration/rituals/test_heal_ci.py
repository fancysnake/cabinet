"""The ci task: a rerun first, then a fix from the log, gated or not, or tests."""

import json

from vekna.trial import Trial

from cabinet.gates.ritual.vekna.heal import (
    close_gap,
    job_gate,
    land_job,
    mend_job,
    pick_job,
    rerun_jobs,
    tend,
)
from cabinet.pacts.heal import (
    Chart,
    CloseGap,
    JobGate,
    LandJob,
    MendJob,
    PickJob,
    RerunJobs,
    SetAside,
    StandDown,
    Tend,
)
from cabinet.pacts.healing import Work
from cabinet.pacts.project import Project
from cabinet.pacts.pulls import Check
from tests.conftest import commit
from tests.integration.rituals.falling import falling
from tests.integration.rituals.keyed import keyed

_SUITE = Check(name="suite", passed=False, id=41)
_LINT = Check(name="lint", passed=False, id=42)
_SUITE_NEXT = Check(name="suite (3.12)", passed=False, id=44)
_PATCH = Check(name="codecov/patch", passed=True, title="96.84% of diff hit", id=43)
_PROJECT = Project.model_validate(
    {
        "ci": {
            "jobs": {
                "suite": {"gate": "mise run test", "fast": "mise run test:unit"},
                "lint": {"rerun": True},
                "codecov/patch": {"covering": True},
            }
        }
    }
)
_LOG = "gh run view --job {id} --log-failed"
_RUNS = (
    "gh api 'repos/{owner}/{repo}/commits/feature/check-runs"
    "?check_name=lint&filter=all&per_page=1'"
)
_GATE = "CI=1 mise run test"
_COVERAGE = "CI=1 mise run diff-cover"
_MISSING = "Diff Coverage\nMissing lines 3-4"
_COMMITTED = "[feature abc123] fix\ncommitted\n"
_SUITE_LOOP = "job_gate-suite"


def _on(work: Work, *red: Check, attended: bool = False) -> Work:
    run = work.run.model_copy(update={"project": _PROJECT, "attended": attended})
    return work.but(run=run).model_copy(update={"red": list(red)})


def _runs(count: int) -> str:
    return json.dumps({"total_count": count, "check_runs": []})


class TestTend:
    @staticmethod
    def test_ci_starts_with_the_reruns(trial: Trial, work: Work) -> None:
        ci = _on(work, _SUITE).but(todos=["ci"])

        assert trial.walk(tend, ci.to(Tend)) == ci.but(todos=[]).to(RerunJobs)


class TestRerunJobs:
    @staticmethod
    def test_a_rerun_ends_the_task(trial: Trial, work: Work) -> None:
        trial.shell.replies(when=_RUNS, stdout=_runs(1))
        trial.shell.replies(when="gh run rerun --job 42")
        red = _on(work, _SUITE, _LINT)

        assert trial.walk(rerun_jobs, red.to(RerunJobs)) == red.but(
            note="reran lint"
        ).to(Tend)

    @staticmethod
    def test_a_check_already_rerun_is_fixed_instead(trial: Trial, work: Work) -> None:
        trial.shell.replies(when=_RUNS, stdout=_runs(2))
        red = _on(work, _LINT)

        assert trial.walk(rerun_jobs, red.to(RerunJobs)) == red.to(PickJob)
        assert "gh run rerun --job 42" not in trial.shell.commands

    @staticmethod
    def test_a_job_without_rerun_is_not_asked_about(trial: Trial, work: Work) -> None:
        red = _on(work, _SUITE)

        assert trial.walk(rerun_jobs, red.to(RerunJobs)) == red.to(PickJob)
        assert not trial.shell.commands

    @staticmethod
    def test_a_rerun_the_forge_refuses_is_noted(trial: Trial, work: Work) -> None:
        trial.shell.replies(when=_RUNS, stdout=_runs(1))
        trial.shell.replies(when="gh run rerun --job 42", exit_code=1, stderr="no")
        red = _on(work, _LINT)

        assert trial.walk(rerun_jobs, red.to(RerunJobs)) == red.but(
            note="gh could not rerun lint: no"
        ).to(PickJob)

    # The share budgets one fix per configured job, and a matrix job's
    # entries all match the one key.
    @staticmethod
    def test_one_check_per_job_is_fixed(trial: Trial, work: Work) -> None:
        red = _on(work, _SUITE, _SUITE_NEXT, _PATCH)

        assert trial.walk(rerun_jobs, red.to(RerunJobs)) == _on(
            work, _SUITE, _PATCH
        ).but(note="left for the next cast, one check per job: suite (3.12)").to(
            PickJob
        )


class TestPickJob:
    @staticmethod
    def test_nothing_left_red_ends_the_task(trial: Trial, work: Work) -> None:
        assert trial.walk(pick_job, _on(work).to(PickJob)) == _on(work).to(Tend)

    @staticmethod
    def test_a_covering_job_is_a_gap(trial: Trial, work: Work) -> None:
        red = _on(work, _PATCH, _SUITE)

        assert trial.walk(pick_job, red.to(PickJob)) == red.to(CloseGap)

    @staticmethod
    def test_any_other_job_is_mended(trial: Trial, work: Work) -> None:
        red = _on(work, _SUITE)

        assert trial.walk(pick_job, red.to(PickJob)) == red.to(MendJob)


class TestMendJob:
    @staticmethod
    def test_a_gated_job_goes_round_its_gate(trial: Trial, work: Work) -> None:
        trial.shell.replies(when=_LOG.format(id=41), stdout="FAILED test_it\n")
        trial.coding.replies("fixed")
        red = _on(work, _SUITE)

        assert trial.walk(mend_job, red.to(MendJob)) == red.to(JobGate)
        prompt = trial.coding.prompts[0]
        assert prompt.startswith("The `suite` CI job is red on this branch.")
        assert "The ritual runs `mise run test` after you" in prompt
        assert prompt.endswith("FAILED test_it\n--- END UNTRUSTED REVIEW DATA ---")

    @staticmethod
    def test_each_job_has_a_session_of_its_own(trial: Trial, work: Work) -> None:
        trial.shell.replies(when=_LOG.format(id=41), stdout="FAILED test_it\n")
        trial.shell.replies(when=_LOG.format(id=42), stdout="E501\n")
        keys = keyed()

        trial.walk(mend_job, _on(work, _SUITE).to(MendJob))
        trial.walk(mend_job, _on(work, _LINT).to(MendJob))

        assert keys == ["job_gate-suite-7", "job_gate-lint-7"]

    # The gate's rounds continue the session that read the log.
    @staticmethod
    def test_the_gate_continues_the_mend(trial: Trial, work: Work) -> None:
        trial.shell.replies(when=_LOG.format(id=41), stdout="FAILED test_it\n")
        trial.shell.replies(when=_GATE, exit_code=1, stdout="1 failed")
        keys = keyed()
        red = _on(work, _SUITE)

        trial.walk(mend_job, red.to(MendJob))
        trial.walk(job_gate, red.to(JobGate))

        assert keys[0] == keys[1]

    @staticmethod
    def test_an_ungated_job_lands_as_the_agent_left_it(
        trial: Trial, work: Work
    ) -> None:
        trial.shell.replies(when=_LOG.format(id=42), stdout="E501\n")
        trial.coding.replies("fixed")
        red = _on(work, _LINT)

        assert trial.walk(mend_job, red.to(MendJob)) == red.to(LandJob)
        assert "the next CI run is the check" in trial.coding.prompts[0]

    @staticmethod
    def test_the_agent_reads_the_end_of_a_long_log(trial: Trial, work: Work) -> None:
        setup = "\n".join(f"step {index} ok" for index in range(4000))
        trial.shell.replies(when=_LOG.format(id=42), stdout=f"{setup}\nE501\n")
        trial.coding.replies("fixed")

        trial.walk(mend_job, _on(work, _LINT).to(MendJob))

        prompt = trial.coding.prompts[0]
        assert prompt.endswith("E501\n--- END UNTRUSTED REVIEW DATA ---")
        assert "step 0 ok" not in prompt

    @staticmethod
    def test_a_gated_job_without_a_log_still_has_its_gate(
        trial: Trial, work: Work
    ) -> None:
        trial.shell.replies(when=_LOG.format(id=41), exit_code=1, stderr="gone")
        red = _on(work, _SUITE)

        assert trial.walk(mend_job, red.to(MendJob)) == red.but(
            note="gh could not read the log of suite: gone"
        ).to(JobGate)
        assert not trial.coding.prompts

    @staticmethod
    def test_an_ungated_job_without_a_log_is_passed_over(
        trial: Trial, work: Work
    ) -> None:
        trial.shell.replies(when=_LOG.format(id=42), exit_code=1, stderr="gone")
        red = _on(work, _LINT, _SUITE)

        assert trial.walk(mend_job, red.to(MendJob)) == red.passed_over(
            "gh could not read the log of lint: gone"
        ).to(PickJob)

    @staticmethod
    def test_an_attended_cast_may_leave_a_job_red(trial: Trial, work: Work) -> None:
        trial.shell.replies(when=_LOG.format(id=42), stdout="E501\n")
        trial.decide.answers(answer=False, when="fix the `lint` job*")
        red = _on(work, _LINT, attended=True)

        assert trial.walk(mend_job, red.to(MendJob)) == red.passed_over(
            "`lint` was left red, as you decided"
        ).to(PickJob)
        assert not trial.coding.prompts

    @staticmethod
    def test_an_agent_that_dies_ends_the_cast(trial: Trial, work: Work) -> None:
        falling()
        trial.shell.replies(when=_LOG.format(id=42), stdout="E501\n")
        red = _on(work, _LINT)

        assert trial.walk(mend_job, red.to(MendJob)) == red.abandoned(
            "the agent stopped mid-flight: boom"
        ).to(Chart)


class TestJobGate:
    @staticmethod
    def test_a_green_gate_lands(trial: Trial, work: Work) -> None:
        trial.shell.replies(when=_GATE)
        red = _on(work, _SUITE)

        assert trial.walk(job_gate, red.to(JobGate)) == red.to(LandJob)

    # The runner named no narrower task, so the job's fast one runs next.
    @staticmethod
    def test_a_red_gate_is_repaired_and_the_fast_task_runs_next(
        trial: Trial, work: Work
    ) -> None:
        trial.shell.replies(when=_GATE, exit_code=1, stdout="1 failed")
        trial.coding.replies("fixed")
        red = _on(work, _SUITE)

        assert trial.walk(job_gate, red.to(JobGate)) == red.but(
            gate="mise run test:unit"
        ).charged(_SUITE_LOOP).to(JobGate)
        assert trial.coding.prompts[0].startswith("`mise run test` is this project")

    @staticmethod
    def test_a_green_fast_task_spends_the_gate(trial: Trial, work: Work) -> None:
        trial.shell.replies(when="CI=1 mise run test:unit")
        red = _on(work, _SUITE).but(gate="mise run test:unit")

        assert trial.walk(job_gate, red.to(JobGate)) == red.but(gate="").to(JobGate)

    @staticmethod
    def test_a_spent_budget_stands_the_branch_down(trial: Trial, work: Work) -> None:
        trial.shell.replies(when=_GATE, exit_code=1, stdout="1 failed")
        spent = _on(work, _SUITE).but(budgets={_SUITE_LOOP: 3})

        assert trial.walk(job_gate, spent.to(JobGate)) == spent.stopped_by(
            "`mise run test` is still red:\n1 failed"
        ).but(run=spent.run.but(seen=["1 failed"])).leaving_red().to(StandDown)

    @staticmethod
    def test_a_stand_down_names_the_checks_left_behind(
        trial: Trial, work: Work
    ) -> None:
        trial.shell.replies(when=_GATE, exit_code=1, stdout="1 failed")
        spent = _on(work, _SUITE, _LINT, _PATCH).but(budgets={_SUITE_LOOP: 3})

        stood = trial.walk(job_gate, spent.to(JobGate))

        assert isinstance(stood, StandDown)
        assert not stood.red
        assert stood.note == "left red behind it: lint, codecov/patch"


class TestCloseGap:
    @staticmethod
    def test_missing_lines_buy_tests_and_the_fast_measurement(
        trial: Trial, work: Work
    ) -> None:
        trial.shell.replies(when=_COVERAGE, stdout=_MISSING)
        trial.coding.replies("covered")
        red = _on(work, _PATCH)

        assert trial.walk(close_gap, red.to(CloseGap)) == red.but(
            gate="mise run test:py:cov:diff"
        ).charged("close_gap-codecov/patch").to(CloseGap)
        assert "Missing lines 3-4" in trial.coding.prompts[0]

    @staticmethod
    def test_a_covered_branch_lands(trial: Trial, work: Work) -> None:
        trial.shell.replies(when=_COVERAGE, stdout="Diff Coverage\nTotal: 100%")
        red = _on(work, _PATCH)

        assert trial.walk(close_gap, red.to(CloseGap)) == red.to(LandJob)

    @staticmethod
    def test_a_covered_fast_measurement_spends_the_full_one(
        trial: Trial, work: Work
    ) -> None:
        trial.shell.replies(when="CI=1 mise run test:py:cov:diff", stdout="Total: 100%")
        red = _on(work, _PATCH).but(gate="mise run test:py:cov:diff")

        assert trial.walk(close_gap, red.to(CloseGap)) == red.but(gate="").to(CloseGap)


class TestLandJob:
    # Green here and red on CI: nothing changed, so nothing is fixed.
    @staticmethod
    def test_a_fix_that_changed_nothing_leaves_the_job_red(
        trial: Trial, work: Work
    ) -> None:
        trial.shell.replies(when="git add -A*")
        red = _on(work, _SUITE, _LINT)

        assert trial.walk(land_job, red.to(LandJob)) == red.passed_over(
            "`suite` passes here; CI is still red"
        ).to(PickJob)

    @staticmethod
    def test_a_fix_is_a_commit_of_its_own(trial: Trial, work: Work) -> None:
        trial.shell.replies(when="git add -A*", stdout=_COMMITTED)
        red = _on(work, _SUITE, _LINT)

        assert trial.walk(land_job, red.to(LandJob)) == red.landed().to(PickJob)
        assert trial.shell.commands == [commit("fix: make the suite job green")]
        assert red.landed().red == [_LINT]

    @staticmethod
    def test_covered_lines_are_a_test_commit(trial: Trial, work: Work) -> None:
        trial.shell.replies(when="git add -A*")

        trial.walk(land_job, _on(work, _PATCH).to(LandJob))

        assert trial.shell.commands == [
            commit("test: cover the lines this branch changes")
        ]

    @staticmethod
    def test_a_commit_that_fails_is_set_aside(trial: Trial, work: Work) -> None:
        trial.shell.replies(when="git add -A*", exit_code=1, stderr="gpg failed")
        red = _on(work, _SUITE)

        assert trial.walk(land_job, red.to(LandJob)) == red.but(
            note="could not commit the suite fix: could not commit: gpg failed"
        ).to(SetAside)
