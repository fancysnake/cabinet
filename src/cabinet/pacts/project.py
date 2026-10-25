"""What one repository tells the rituals about itself.

Read from the `[cabinet]` section of the repository's `.vekna.toml`, validated
at the boundary so a misspelled key dies before a branch is checked out. The
values are strings: a task name is only tested by running it.
"""

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field
from vekna.lexicon import RitualError

Forge = Literal["github", "gitlab"]
Effort = Literal["low", "medium", "high", "xhigh", "max"]


class ConfigError(RitualError):
    pass


# One label as the forge should hold it. The colour is a hex triplet without
# the hash; each forge spells it its own way.
class LabelSpec(BaseModel):
    name: str
    color: str
    description: str


# A label exists only to stop a ritual repeating something it put on the pull
# request. A fact that goes away once it is fixed (a conflict, a red check)
# needs none.
class Labels(BaseModel):
    model_config = ConfigDict(extra="forbid")

    # This branch has had its review. Inline review comments are invisible to a
    # listing, so a label is what a step can see — and a label is something
    # you can take off, which is how you ask for the review again.
    reviewed: str = "pr::thermo"
    # Hands off. Read at the listing and nowhere else, so a branch wearing it is
    # never taken, never touched, never reported on.
    wait: str = "pr::wait"
    # The guide was posted; remove to ask for it again.
    qa: str = "v:guide:done"

    # Every label `heal` reads or puts on, with what it means, for the forge.
    def conjured(self) -> list[LabelSpec]:
        return [
            LabelSpec(
                name=self.reviewed,
                color="0e8a16",
                description="A quality review was posted; remove to ask again",
            ),
            LabelSpec(
                name=self.wait,
                color="d93f0b",
                description="Hands off: the rituals leave this one alone",
            ),
            LabelSpec(
                name=self.qa,
                color="c5def5",
                description="The smoke-test guide was posted; remove to ask again",
            ),
        ]


# What a label ritual leaves behind: every label it made or refreshed.
class Labelled(BaseModel):
    names: list[str]


# One CI job the rituals may fix. A job listed bare is still one whose red
# makes a `ci` todo.
class CiJob(BaseModel):
    model_config = ConfigDict(extra="forbid")

    # Red here is missing coverage; its summary may name the patch coverage
    # ("96.84% of diff hit"). Fixed by the coverage loop, which measures with
    # `gate` and `fast` where they are set and the project's own coverage
    # commands where they are not.
    covering: bool = False
    # Red here may be a flake: run it again once before anything is fixed.
    rerun: bool = False
    # The command that reproduces the job here. Empty is a job nothing runs
    # locally: the agent gets one attempt from the log, and the next CI run is
    # the check.
    gate: str = ""
    # The narrower command re-run between repair rounds; empty is `gate`.
    fast: str = ""


def _jobs() -> dict[str, CiJob]:
    return {"checks": CiJob(), "test": CiJob(), "codecov/patch": CiJob(covering=True)}


# The CI jobs the rituals read, keyed by a prefix of the check's name as the
# forge reports it. A check no key matches is not the rituals' business.
class Ci(BaseModel):
    model_config = ConfigDict(extra="forbid")

    jobs: dict[str, CiJob] = Field(default_factory=_jobs)

    # The key a check belongs to: the longest it starts with, so
    # `codecov/patch` beats `codecov/` for the check both would match.
    def key(self, check: str) -> str | None:
        keys = [key for key in self.jobs if check.startswith(key)]
        return max(keys, key=len) if keys else None

    def job(self, check: str) -> CiJob | None:
        key = self.key(check)
        return None if key is None else self.jobs[key]

    def covering(self, check: str) -> bool:
        job = self.job(check)
        return job is not None and job.covering


class Agent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    model: str = "opus"
    effort: Effort = "high"
    # Zero is unbounded; the SDK's own default.
    max_turns: Annotated[int, Field(ge=0)] = 0
    # The repository's own slow tasks, a full e2e suite, say. The prompt names
    # them beside the gate and the coverage commands, so an agent checks
    # itself with something narrower. Advice, not a lock.
    may_not_run: list[str] = []


class Project(BaseModel):
    model_config = ConfigDict(extra="forbid")

    forge: Forge = "github"
    base: str = "main"
    # Pushed to and fetched from by name. Must be https with the forge CLI as
    # its credential helper: a command under a cast has no terminal for ssh to
    # ask a passphrase on.
    remote: str = "origin"
    gate: str = "mise run pr-fix"
    coverage: str = "mise run diff-cover"
    # The same measurement without the slow suites, re-run between repair
    # rounds. The full one runs once more at the end and is what counts.
    fast_coverage: str = "mise run test:py:cov:diff"
    # Off for a repository whose commits are signed with a key nobody can
    # unlock at 3am: the commit then runs with `commit.gpgsign=false`.
    sign_commits: bool = True
    review_skill: str = "~/.claude/skills/thermo-nuclear-code-quality-review/SKILL.md"
    review_title: str = "Thermo-nuclear code quality review"
    # The skill file `identify` has the agent read once, at the top of its
    # session: what the types and sizes mean and how issues are linked.
    identify_skill: str = "~/.claude/skills/issues/SKILL.md"
    labels: Labels = Labels()
    ci: Ci = Ci()
    agent: Agent = Agent()

    # The long tasks an agent is asked to leave alone: the ones the ritual runs
    # itself as soon as the agent stops, and the project's own slow ones.
    def long_tasks(self) -> list[str]:
        named = (self.gate, self.coverage, self.fast_coverage)
        # A value spelled out: with none, or `None`, its values type as `Any`.
        listed = (*named, *self.agent.may_not_run)
        return list(dict.fromkeys(listed, True))


# `conjure`'s payload: which labels to make, and on which forge. Its own class
# rather than the `Project` itself: a step owns the class it takes, and the
# project is everybody's.
class Conjure(BaseModel):
    project: Project
    specs: list[LabelSpec]
