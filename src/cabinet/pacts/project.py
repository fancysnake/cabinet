"""What one repository tells the rituals about itself.

Read from the `[cabinet]` section of the repository's `.vekna.toml`, validated
at the boundary so a typo in a task name dies before a branch is checked out.
"""

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field
from vekna.lexicon import RitualError

Forge = Literal["github", "gitlab"]
Effort = Literal["low", "medium", "high", "xhigh", "max"]
State = Literal["started", "done"]


class ConfigError(RitualError):
    pass


# One label as the forge should hold it. The colour is a hex triplet without
# the hash; each forge spells it its own way.
class LabelSpec(BaseModel):
    name: str
    color: str
    description: str


# The rituals that mark checkpoints, and so the ones whose markers are made.
_MARKED = ("refresh", "cover", "review")


class Labels(BaseModel):
    model_config = ConfigDict(extra="forbid")

    # This branch has had its review. Inline review comments are invisible to a
    # listing, so a label is what a step can see — and a label is something
    # you can take off, which is how you ask for the review again.
    reviewed: str = "pr::thermo"
    # Hands off. Read at the listing and nowhere else, so a branch wearing it is
    # never taken, never touched, never reported on.
    wait: str = "pr::wait"
    # The prefix a ritual's checkpoints wear: `v:refresh:started`.
    marker: str = "v"

    def checkpoint(self, ritual: str, state: State) -> str:
        return f"{self.marker}:{ritual}:{state}"

    # Every label the rituals read or write, with what it means, for the forge.
    def conjured(self) -> list[LabelSpec]:
        named = [
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
        ]
        for ritual in _MARKED:
            named += [
                LabelSpec(
                    name=self.checkpoint(ritual, "started"),
                    color="fbca04",
                    description=f"{ritual} began on this branch and has not finished",
                ),
                LabelSpec(
                    name=self.checkpoint(ritual, "done"),
                    color="c5def5",
                    description=f"{ritual} ended clean on this branch",
                ),
            ]
        return named


# What `labels` leaves behind: every label it made or refreshed.
class Labelled(BaseModel):
    names: list[str]


# The names CI gives the jobs the rituals read. Prefixes, matched against the
# check's name as the forge reports it.
class Ci(BaseModel):
    model_config = ConfigDict(extra="forbid")

    # Red here means `gate` is worth running; anything else on the board is not
    # this pass's business.
    gate_checks: list[str] = ["checks", "test"]
    # Red here means the coverage pass is worth its hour.
    cover_checks: list[str] = ["codecov/", "test"]
    # The check whose summary names the patch coverage ("96.84% of diff hit").
    patch_check: str = "codecov/patch"


class Agent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    model: str = "opus"
    effort: Effort = "high"
    # Zero is unbounded; the SDK's own default.
    max_turns: Annotated[int, Field(ge=0)] = 0
    # Command prefixes an agent may run itself, on top of read-only git. Each
    # becomes a `Bash(<prefix>:*)` allowlist entry, so what the prompt says
    # and what the SDK permits are the same list.
    may_run: list[str] = []


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
    labels: Labels = Labels()
    ci: Ci = Ci()
    agent: Agent = Agent()
