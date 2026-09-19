"""How much an agent is allowed to reach, and what a failed call comes back as."""

from pydantic import BaseModel
from vekna.folio.coding_claude import ClaudeOptions
from vekna.lexicon import Transition, done, step
from vekna.trial import Trial

from cabinet.links.agent.claude import ClaudeAgent, allowed_tools
from cabinet.pacts.agent import Fallen, Misread, Role
from cabinet.pacts.project import Project
from cabinet.pacts.threads import TriageNotes

_PROJECT = Project.model_validate(
    {"agent": {"may_run": ["mise run test:unit"], "max_turns": 30}}
)
_READER = [
    "Read",
    "Grep",
    "Glob",
    "Bash(git diff:*)",
    "Bash(git log:*)",
    "Bash(git show:*)",
    "Bash(git status:*)",
    "Bash(git blame:*)",
]
_WRITER = [*_READER, "Edit", "Write", "MultiEdit", "Bash(mise run test:unit:*)"]


class _Ask(BaseModel):
    role: Role = "writer"
    key: str | None = None
    attended: bool = False


class _Came(BaseModel):
    fallen: Fallen | None = None
    misread: Misread | None = None
    notes: TriageNotes | None = None


@step
async def ask(asked: _Ask) -> Transition:
    fallen = await ClaudeAgent(_PROJECT).ask(
        "do it", role=asked.role, key=asked.key, attended=asked.attended
    )
    return done(_Came(fallen=fallen))


@step
async def ask_twice(asked: _Ask) -> Transition:
    agent = ClaudeAgent(_PROJECT)
    await agent.ask("do it", role=asked.role, key=asked.key)
    await agent.ask("do it again", role=asked.role, key=asked.key)
    return done()


@step
async def ask_for(asked: _Ask) -> Transition:
    came = await ClaudeAgent(_PROJECT).ask_for(
        "read it",
        output=TriageNotes,
        role=asked.role,
        key=asked.key,
        attended=asked.attended,
    )
    if isinstance(came, Fallen):
        return done(_Came(fallen=came))
    if isinstance(came, Misread):
        return done(_Came(misread=came))
    return done(_Came(notes=came))


class TestAllowedTools:
    @staticmethod
    def test_a_reader_sees_and_runs_read_only_git() -> None:
        assert allowed_tools("reader", _PROJECT) == _READER

    @staticmethod
    def test_a_writer_edits_and_runs_what_the_project_allows() -> None:
        assert allowed_tools("writer", _PROJECT) == _WRITER

    @staticmethod
    def test_a_resolver_may_also_stage() -> None:
        assert allowed_tools("resolver", _PROJECT) == [*_WRITER, "Bash(git add:*)"]

    @staticmethod
    def test_a_project_allowing_nothing_gives_no_bash_beyond_git() -> None:
        assert allowed_tools("writer", Project()) == [
            *_READER,
            "Edit",
            "Write",
            "MultiEdit",
        ]


class TestAsk:
    @staticmethod
    def test_every_call_is_bound_by_its_role(trial: Trial) -> None:
        trial.coding.replies("did it")

        assert trial.walk(ask, _Ask(role="resolver")) == done(_Came())
        assert trial.coding.calls[0].model == "opus"
        assert trial.coding.calls[0].focus_options == ClaudeOptions(
            permission_mode="dontAsk",
            allowed_tools=[*_WRITER, "Bash(git add:*)"],
            effort="high",
            max_turns=30,
        )
        assert trial.coding.calls[0].resume is None

    @staticmethod
    def test_an_attended_call_runs_in_auto_mode(trial: Trial) -> None:
        trial.coding.replies("did it")

        trial.walk(ask, _Ask(attended=True))

        assert trial.coding.calls[0].focus_options == ClaudeOptions(
            permission_mode="auto", allowed_tools=_WRITER, effort="high", max_turns=30
        )

    @staticmethod
    def test_a_keyed_call_continues_its_thread(trial: Trial) -> None:
        trial.coding.replies("first")
        trial.coding.replies("second")

        trial.walk(ask_twice, _Ask(key="repair"))

        assert trial.coding.calls[0].resume is None
        assert trial.coding.calls[1].resume == "s1"

    # An empty key is refused by the medium itself, which is the one failure
    # this test can make happen from the outside.
    @staticmethod
    def test_a_medium_that_raises_comes_back_as_fallen(trial: Trial) -> None:
        transition = trial.walk(ask, _Ask(key=""))

        assert isinstance(transition, type(done()))
        assert isinstance(transition.result, _Came)
        assert transition.result.fallen is not None
        assert "stopped mid-flight" in transition.result.fallen.reason
        assert not trial.coding.calls


class TestAskFor:
    @staticmethod
    def test_the_answer_is_validated(trial: Trial) -> None:
        trial.coding.replies(TriageNotes(items=[]))

        assert trial.walk(ask_for, _Ask(role="reader")) == done(
            _Came(notes=TriageNotes(items=[]))
        )
        assert trial.coding.calls[0].focus_options == ClaudeOptions(
            permission_mode="dontAsk",
            allowed_tools=_READER,
            effort="high",
            max_turns=30,
        )

    @staticmethod
    def test_an_answer_in_the_wrong_shape_is_a_misread(trial: Trial) -> None:
        trial.coding.replies("no idea, sorry")

        transition = trial.walk(ask_for, _Ask(role="reader"))

        assert isinstance(transition, type(done()))
        assert isinstance(transition.result, _Came)
        assert transition.result.misread is not None
        assert "did not answer in the shape asked" in transition.result.misread.reason

    @staticmethod
    def test_a_medium_that_raises_comes_back_as_fallen(trial: Trial) -> None:
        transition = trial.walk(ask_for, _Ask(role="reader", key=""))

        assert isinstance(transition, type(done()))
        assert isinstance(transition.result, _Came)
        assert transition.result.fallen is not None
