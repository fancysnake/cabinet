"""Which tools an agent gets, and what a failed call comes back as."""

from vekna.folio.coding_claude import ClaudeOptions
from vekna.trial import Trial

from cabinet.links.agent.claude import ClaudeAgent, allowed_tools
from cabinet.pacts.agent import Fallen, Misread
from cabinet.pacts.project import Project
from cabinet.pacts.threads import TriageNotes
from tests.conftest import drive

_PROJECT = Project.model_validate({"agent": {"max_turns": 30}})
_READER = ["Read", "Grep", "Glob", "Bash"]
_WRITER = [*_READER, "Edit", "Write", "MultiEdit"]
_AGENT = ClaudeAgent(_PROJECT)


class TestAllowedTools:
    @staticmethod
    def test_a_reader_reads_and_has_a_shell() -> None:
        assert allowed_tools("reader") == _READER

    @staticmethod
    def test_a_writer_also_edits() -> None:
        assert allowed_tools("writer") == _WRITER


class TestAsk:
    @staticmethod
    def test_every_call_is_bound_by_its_role(trial: Trial) -> None:
        trial.coding.replies("did it")

        assert (
            drive(trial, lambda: _AGENT.ask("do it", job="fix", role="writer")) is None
        )
        assert trial.coding.calls[0].model == "sonnet"
        assert trial.coding.calls[0].focus_options == ClaudeOptions(
            permission_mode="dontAsk",
            allowed_tools=_WRITER,
            effort="high",
            max_turns=30,
        )
        assert trial.coding.calls[0].resume is None

    @staticmethod
    def test_the_job_picks_the_model(trial: Trial) -> None:
        trial.coding.replies("did it")
        agent = ClaudeAgent(
            Project.model_validate({"agent": {"models": {"fix": "claude-opus-5-5"}}})
        )

        drive(trial, lambda: agent.ask("do it", job="fix", role="writer"))

        assert trial.coding.calls[0].model == "claude-opus-5-5"

    @staticmethod
    def test_an_attended_call_runs_in_auto_mode(trial: Trial) -> None:
        trial.coding.replies("did it")

        attended = ClaudeAgent(_PROJECT, attended=True)

        drive(trial, lambda: attended.ask("do it", job="fix", role="writer"))

        assert trial.coding.calls[0].focus_options == ClaudeOptions(
            permission_mode="auto", allowed_tools=_WRITER, effort="high", max_turns=30
        )

    @staticmethod
    def test_a_keyed_call_continues_its_thread(trial: Trial) -> None:
        trial.coding.replies("first")
        trial.coding.replies("second")

        async def twice() -> None:
            await _AGENT.ask("do it", job="fix", role="writer", key="repair")
            await _AGENT.ask("do it again", job="fix", role="writer", key="repair")

        drive(trial, twice)

        assert trial.coding.calls[0].resume is None
        assert trial.coding.calls[1].resume == "s1"

    # An empty key is refused by the medium itself, which is the one failure
    # this test can make happen from the outside.
    @staticmethod
    def test_a_medium_that_raises_comes_back_as_fallen(trial: Trial) -> None:
        came = drive(
            trial, lambda: _AGENT.ask("do it", job="fix", role="writer", key="")
        )

        assert isinstance(came, Fallen)
        assert "stopped mid-flight" in came.reason
        assert not trial.coding.calls


class TestAskFor:
    @staticmethod
    def test_the_answer_is_validated(trial: Trial) -> None:
        trial.coding.replies(TriageNotes(items=[]))

        came = drive(
            trial,
            lambda: _AGENT.ask_for(
                "read it", output=TriageNotes, job="plan", role="reader"
            ),
        )

        assert came == TriageNotes(items=[])
        assert trial.coding.calls[0].model == "opus"
        assert trial.coding.calls[0].focus_options == ClaudeOptions(
            permission_mode="dontAsk",
            allowed_tools=_READER,
            effort="high",
            max_turns=30,
        )

    @staticmethod
    def test_an_answer_in_the_wrong_shape_is_a_misread(trial: Trial) -> None:
        trial.coding.replies("no idea, sorry")

        came = drive(
            trial,
            lambda: _AGENT.ask_for(
                "read it", output=TriageNotes, job="plan", role="reader"
            ),
        )

        assert isinstance(came, Misread)
        assert "did not answer in the shape asked" in came.reason

    @staticmethod
    def test_a_medium_that_raises_comes_back_as_fallen(trial: Trial) -> None:
        came = drive(
            trial,
            lambda: _AGENT.ask_for(
                "read it", output=TriageNotes, job="plan", role="reader", key=""
            ),
        )

        assert isinstance(came, Fallen)
