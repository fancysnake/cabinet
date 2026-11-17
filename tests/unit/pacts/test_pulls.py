"""The board as a survey reads it: each check with the job it belongs to."""

from cabinet.pacts.project import Project
from cabinet.pacts.pulls import Board, Check


class TestWatched:
    @staticmethod
    def test_a_covering_job_without_commands_measures_with_the_projects() -> None:
        board = Board(checks=[Check(name="codecov/patch", id=1)])

        job = board.watched(Project(coverage="full", fast_coverage="quick"))[0].job

        assert (job.gate, job.fast) == ("full", "quick")

    @staticmethod
    def test_a_covering_job_keeps_the_commands_it_names() -> None:
        cov = {"covering": True, "gate": "mine", "fast": "mini"}
        project = Project.model_validate({"ci": {"jobs": {"cov": cov}}})

        job = Board(checks=[Check(name="cov", id=1)]).watched(project)[0].job

        assert (job.gate, job.fast) == ("mine", "mini")

    @staticmethod
    def test_another_job_gets_no_default_gate() -> None:
        job = Board(checks=[Check(name="test", id=1)]).watched(Project())[0].job

        assert not job.gate
