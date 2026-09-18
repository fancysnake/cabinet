"""Where the layers meet: one object holding every service a step reaches.

Bound into the pacts slot by `wire()`, which `cabinet.rituals` calls once as
it is imported, from `cabinet.rituals.wiring` — the one moment vekna gives a
tome before any step runs.
"""

from functools import cached_property
from pathlib import Path
from typing import TYPE_CHECKING, override

from cabinet.links.agent.claude import ClaudeAgent
from cabinet.links.config.vekna_toml import read_project
from cabinet.links.forge.github import GithubForge
from cabinet.links.forge.gitlab import GitlabForge
from cabinet.links.scm.git import GitScm
from cabinet.links.tasks.mise import MiseTasks
from cabinet.mills.prompts import Prompts
from cabinet.mills.pulls import Pulls
from cabinet.mills.repairs import Repairs
from cabinet.mills.report import Report
from cabinet.mills.verdicts import Verdicts
from cabinet.pacts.services import ServicesProtocol, bind

if TYPE_CHECKING:
    from cabinet.pacts.agent import AgentProtocol
    from cabinet.pacts.forge import ForgeProtocol
    from cabinet.pacts.project import Project
    from cabinet.pacts.scm import ScmProtocol
    from cabinet.pacts.tasks import TasksProtocol


class Services(ServicesProtocol):
    @cached_property
    @override
    def pulls(self) -> Pulls:
        return Pulls()

    @cached_property
    @override
    def verdicts(self) -> Verdicts:
        return Verdicts()

    @cached_property
    @override
    def prompts(self) -> Prompts:
        return Prompts()

    @cached_property
    @override
    def repairs(self) -> Repairs:
        return Repairs(self.prompts, self.verdicts)

    @cached_property
    @override
    def report(self) -> Report:
        return Report()

    # The cwd, because that is where vekna found the `.vekna.toml` naming this
    # tome, and the same walk finds the same file.
    @override
    def project(self) -> Project:
        return read_project(Path.cwd())

    # Both forges are wired; which one answers is the repository's own choice.
    @override
    def forge(self, project: Project) -> ForgeProtocol:
        if project.forge == "gitlab":
            return GitlabForge()
        return GithubForge()

    @override
    def scm(self, project: Project) -> ScmProtocol:
        return GitScm(project)

    @override
    def tasks(self, project: Project) -> TasksProtocol:
        return MiseTasks()

    @override
    def agent(self, project: Project) -> AgentProtocol:
        return ClaudeAgent(project)


def wire() -> None:
    bind(Services())
