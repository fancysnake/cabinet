"""The services a step reaches, and the one seam they reach them through.

vekna finds steps by sweeping a module and routes between them by reference,
so nothing constructs a step and nothing can inject into one. What is left is
the seam vekna itself uses for its foci: a slot filled once, at wiring, and
read at call time. `inits` binds it; a step reads it; nothing else touches it.
"""

from typing import TYPE_CHECKING, Protocol

from vekna.lexicon import RitualError

if TYPE_CHECKING:
    from cabinet.pacts.agent import AgentProtocol
    from cabinet.pacts.forge import ForgeProtocol
    from cabinet.pacts.project import Project
    from cabinet.pacts.pulls import Board, PullRequest, Run
    from cabinet.pacts.repairs import Attempt, Ruling
    from cabinet.pacts.reviews import Picking
    from cabinet.pacts.scm import ScmProtocol
    from cabinet.pacts.tasks import Ran, TasksProtocol
    from cabinet.pacts.threads import Finding, Thread, TriageItem


class PullsProtocol(Protocol):
    # Parked branches dropped, oldest-modified first.
    def wanted(
        self, pulls: list[PullRequest], project: Project
    ) -> list[PullRequest]: ...

    # True unless the board positively says the coverage is fine.
    def wants_cover(self, board: Board, project: Project) -> bool: ...

    # False unless the board positively says the gate jobs are green.
    def gates_green(self, board: Board, project: Project) -> bool: ...


class VerdictsProtocol(Protocol):
    # Both streams, trimmed to the budget an agent is worth reading.
    def said(self, ran: Ran) -> str: ...

    # The last dozen lines of what the tool said, for a person.
    def verdict(self, ran: Ran) -> str: ...

    # The one task the runner named as broken, or empty where it did not.
    def narrowed(self, ran: Ran) -> str: ...

    # The coverage report from its banner on, or the trimmed log where none
    # was printed.
    def coverage_report(self, ran: Ran) -> str: ...

    # Whether the report names a line no test reached.
    def uncovered(self, report: str) -> bool: ...

    def already_seen(self, verdict: str, seen: list[str]) -> bool: ...


class PromptsProtocol(Protocol):
    def resolve(
        self, project: Project, *, base: str, branch: str, files: str
    ) -> str: ...

    def fix_gates(self, project: Project, output: str, *, gate: str) -> str: ...

    def cover_gap(self, project: Project, report: str, *, partial: bool) -> str: ...

    def triage_read(self, number: int, threads: list[Thread]) -> str: ...

    def triage_work(
        self, number: int, items: list[TriageItem], told: list[str]
    ) -> str: ...

    def review(
        self, project: Project, *, base: str, threads: list[Thread], reason: str
    ) -> str: ...


class RepairsProtocol(Protocol):
    # What one round of a repair loop comes to: green, given up on, or one
    # more attempt with the asking already written.
    def ruling(self, attempt: Attempt) -> Ruling: ...


class ReportProtocol(Protocol):
    # The review's items as they go on the pull request, each headed with the
    # review's own title.
    def findings(self, project: Project, found: list[Finding]) -> list[Finding]: ...

    def sweep(self, run: Run) -> str: ...

    def review(self, picking: Picking) -> str: ...

    def triage(self, items: list[TriageItem]) -> list[str]: ...

    def shown(self, index: int, item: TriageItem) -> str: ...


class ServicesProtocol(Protocol):
    @property
    def pulls(self) -> PullsProtocol: ...

    @property
    def verdicts(self) -> VerdictsProtocol: ...

    @property
    def prompts(self) -> PromptsProtocol: ...

    @property
    def repairs(self) -> RepairsProtocol: ...

    @property
    def report(self) -> ReportProtocol: ...

    # What the repository standing at the cwd says about itself.
    def project(self) -> Project: ...

    def forge(self, project: Project) -> ForgeProtocol: ...

    def scm(self, project: Project) -> ScmProtocol: ...

    def tasks(self, project: Project) -> TasksProtocol: ...

    def agent(self, project: Project) -> AgentProtocol: ...


class ServicesUnboundError(RitualError):
    pass


_BOUND: list[ServicesProtocol] = []


def bind(bound: ServicesProtocol) -> None:
    _BOUND[:] = [bound]


def services() -> ServicesProtocol:
    if not _BOUND:
        msg = "no services bound: cast through cabinet.rituals, which wires them"
        raise ServicesUnboundError(msg)
    return _BOUND[0]
