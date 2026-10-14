"""What a heal cast carries, and what its survey makes of each pull request."""

from typing import Literal, Self, TypeVar

from pydantic import BaseModel, Field

from cabinet.pacts.hops import Hop
from cabinet.pacts.project import Project
from cabinet.pacts.pulls import Board, PullRequest
from cabinet.pacts.threads import Thread

_HealingT = TypeVar("_HealingT", bound="Healing")

# What a branch may need next, in the order a cast does it: the base merged
# in, CI made green, the threads answered, a review posted, the guide posted:
# the smoke-test instructions, as a comment.
Todo = Literal["merge", "ci", "answer", "review", "guide"]

# `this` is the branch at the cwd; `mine` is every open pull request of yours.
Scope = Literal["this", "mine"]


class Heal(BaseModel):
    # Survey, say what each branch needs, and change nothing.
    plan_only: bool = False


# Everything the survey reads about one pull request, read once.
class Facts(BaseModel):
    pull: PullRequest
    board: Board
    threads: list[Thread]
    # The forge's answer where it had one, git's where it did not.
    conflicted: bool


# What the survey made of one pull request. `note` is why it could not tell,
# where it could not: such a row has no todos, because none were read.
class Surveyed(BaseModel):
    number: int
    branch: str
    url: str
    todos: list[Todo] = []
    # The configured CI jobs whose checks are red, and the open threads: what
    # `ci` and `answer` would work through.
    red: list[str] = []
    threads: int = 0
    note: str = ""


class Plan(BaseModel):
    surveyed: list[Surveyed] = []


class Healing(Hop):
    project: Project
    scope: Scope
    queue: list[PullRequest] = Field(default_factory=list)
    surveyed: list[Surveyed] = Field(default_factory=list)

    def to(self, kind: type[_HealingT]) -> _HealingT:
        return self._rebuilt(kind)

    def queued(self, queue: list[PullRequest]) -> Self:
        update: dict[str, list[PullRequest]] = {"queue": queue}
        return self.model_copy(update=update)

    # The head of the queue taken off it, its row added.
    def took(self, row: Surveyed) -> Self:
        update: dict[str, list[PullRequest] | list[Surveyed]] = {
            "queue": self.queue[1:],
            "surveyed": [*self.surveyed, row],
        }
        return self.model_copy(update=update)
