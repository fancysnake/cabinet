"""What the refinement cast carries from page to page."""

from typing import Literal, Self

from pydantic import BaseModel

from cabinet.pacts.project import Kind, Project, Size
from cabinet.pacts.reviews import Batch


# One open issue as the forge lists it.
class Issue(BaseModel):
    number: int
    title: str
    url: str
    body: str = ""
    labels: list[str] = []


class Refine(BaseModel):
    batch: Batch = 7


# What the refiner says it did to one issue. Read for the report and nothing
# else: the labels, sub-issues and links are already on the forge by the time
# this comes back.
class RefinedItem(BaseModel):
    number: int
    kind: Kind
    # None on an epic, which is sized by its sub-issues.
    size: Size | None = None
    epic: bool = False
    # The sub-issues opened under it.
    created: list[int] = []
    # The issues it now points at: blocked-by, sub-issue of, related.
    linked: list[int] = []
    note: str = ""


class Refined(BaseModel):
    items: list[RefinedItem]


Outcome = Literal["refined", "declined", "missed", "stopped"]


# One issue's ending, and what the refiner said it did where it did anything.
class Refinement(BaseModel):
    number: int
    outcome: Outcome
    item: RefinedItem | None = None


# What the cast is still to do and what it has done.
class Refining(BaseModel):
    project: Project
    batch: Batch = 7
    queue: list[Issue] = []
    refined: list[Refinement] = []
    # Whether the refiner has been told to read the skill. Once a cast: every
    # page after the first continues the session that read it.
    briefed: bool = False
    stopped: str = ""

    # `None` means "whatever this one had", as every other payload's builder.
    def but(
        self,
        *,
        queue: list[Issue] | None = None,
        refined: list[Refinement] | None = None,
        briefed: bool | None = None,
        stopped: str | None = None,
    ) -> Self:
        update: dict[str, list[Issue] | list[Refinement] | bool | str] = {}
        if queue is not None:
            update["queue"] = queue
        if refined is not None:
            update["refined"] = refined
        if briefed is not None:
            update["briefed"] = briefed
        if stopped is not None:
            update["stopped"] = stopped
        return self.model_copy(update=update)

    def rowed(self, rows: list[Refinement]) -> Self:
        return self.but(refined=[*self.refined, *rows])


# The issues one agent call refines, and the rest of the cast riding along.
class Page(BaseModel):
    refining: Refining
    issues: list[Issue]

    # Every issue on the page ending the same way: declined, or stopped.
    def rowed(self, outcome: Outcome) -> Refining:
        return self.refining.rowed(
            [Refinement(number=one.number, outcome=outcome) for one in self.issues]
        )
