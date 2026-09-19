"""What the review-answering cast carries from branch to branch."""

from typing import Annotated, Literal, Self

from pydantic import BaseModel, Field

from cabinet.pacts.budgets import Budgeted
from cabinet.pacts.project import Project
from cabinet.pacts.pulls import Bound, PullRequest
from cabinet.pacts.threads import Answer, TriageItem

# How many open threads one round reads, answers and settles before the next
# round fetches what is left. Forty threads at once is one triage nobody holds
# in their head and one agent asked to fix forty things before anything is
# posted. No ceiling: a batch bigger than the review is the whole review.
Batch = Annotated[int, Field(ge=1)]


class Review(BaseModel):
    bound: Bound = 3
    batch: Batch = 7


Outcome = Literal["shipped", "declined", "elsewhere", "unread", "nothing", "stopped"]


# One branch's ending, in the words of the step that ended it. A branch with
# nothing open gets none of these: most have nothing open, and a report that
# says so line by line is a report nobody reads to the end.
class Reviewed(BaseModel):
    branch: str
    outcome: Outcome
    note: str = ""


# What the cast is still to do and what it has done. Carried through every
# step, because every ending goes round again — and the last one owes the
# report.
class Picking(BaseModel):
    project: Project
    bound: Bound
    batch: Batch = 7
    queue: list[PullRequest] = []
    reviewed: list[Reviewed] = []
    stopped: str = ""

    # `None` means "whatever this one had", the same as every other payload's
    # builder: an empty string is a value, and passing one clears the field.
    def but(
        self,
        *,
        queue: list[PullRequest] | None = None,
        reviewed: list[Reviewed] | None = None,
        stopped: str | None = None,
    ) -> Self:
        update: dict[str, list[PullRequest] | list[Reviewed] | str] = {}
        if queue is not None:
            update["queue"] = queue
        if reviewed is not None:
            update["reviewed"] = reviewed
        if stopped is not None:
            update["stopped"] = stopped
        return self.model_copy(update=update)


class Branch(BaseModel):
    # The rest of the cast, riding along: a branch is taken off the queue when
    # it is picked, so what is here is what comes after this one.
    picking: Picking
    name: str
    # Carried rather than looked up again: review threads are addressed by
    # pull request and not by branch.
    number: int
    # Threads answered on this branch so far, round by round. Zero is a branch
    # nothing has touched, which is the only one that can still be walked
    # away from without a commit.
    answered: int = 0

    @property
    def bound(self) -> int:
        return self.picking.bound

    @property
    def batch(self) -> int:
        return self.picking.batch

    # Another round posted and settled.
    def taken(self, count: int) -> Self:
        update: dict[str, int] = {"answered": self.answered + count}
        return self.model_copy(update=update)

    @property
    def project(self) -> Project:
        return self.picking.project

    # What this branch's turn came to, written where its turn ended.
    def rowed(self, outcome: Outcome, note: str = "") -> Picking:
        row = Reviewed(branch=self.name, outcome=outcome, note=note)
        return self.picking.but(reviewed=[*self.picking.reviewed, row])


class Triage(BaseModel):
    branch: Branch
    items: list[TriageItem]


class Instructed(BaseModel):
    branch: Branch
    # The whole thing the agent is sent, assembled where the triage and your
    # answers to it are both in hand. It is also what the grimoire then shows.
    prompt: str
    # The threads the answers are owed under, so the step that posts them can
    # tell one the agent made up from one that was triaged.
    threads: list[str]


# What the agent answered, one entry per triaged thread, waiting to be posted
# by the step that can reach the forge.
class Answering(BaseModel):
    branch: Branch
    items: list[Answer]
    threads: list[str]


# Budgeted like every other repair loop: the attempts are counted per step,
# and a task going green on its own hands the count back.
class Landing(Budgeted):
    branch: Branch
    # The task that broke last time, where the runner named one. Empty is the
    # whole gate, which is what runs first and what has the last word.
    gate: str = ""

    def but(self, *, gate: str) -> Self:
        update: dict[str, str] = {"gate": gate}
        return self.model_copy(update=update)
