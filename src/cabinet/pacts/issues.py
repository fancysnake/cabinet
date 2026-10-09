"""What an issue is to the rituals, and what the identification cast carries.

The vocabulary lives here rather than with the repository's own configuration
because it is not the repository's to choose: the `issues` skill the agent
reads names the same types, sizes and epic label, and a project that renamed
them would be identified against words its agent has never heard.
"""

from typing import Literal, Self, TypeVar, get_args

from pydantic import BaseModel, Field

from cabinet.pacts.budgets import BATCH, Batch
from cabinet.pacts.hops import Hop
from cabinet.pacts.project import LabelSpec, Project

_IdentifyingT = TypeVar("_IdentifyingT", bound="Identifying")


# One open issue as the forge lists it.
class Issue(BaseModel):
    number: int
    title: str
    url: str
    body: str = ""
    labels: list[str] = []
    author: str = ""


# Your open issues as the forge gave them, and whether it gave them all: a
# listing that hit its cap hides the rest, and a hidden issue looks exactly
# like a identified one.
class Listing(BaseModel):
    issues: list[Issue] = []
    truncated: bool = False


# An issue the ritual opened: the number to attach and report it by, and the
# URL to name it by.
class Opened(BaseModel):
    number: int
    url: str


# What an issue is and how big, as identification labels it. Bare names rather
# than prefixed ones: these are the labels a backlog already wears, and
# GitHub's issue types carry the same words.
Kind = Literal["feature", "edit", "chore", "spike", "bug"]
Size = Literal["S", "M", "L"]
KINDS: tuple[Kind, ...] = get_args(Kind)
SIZES: tuple[Size, ...] = get_args(Size)
EPIC = "epic"

# Every label identification reads or writes, with what it means, for the forge.
# Read by `labels.identify` to make them and by the prompt to say what they mean,
# so the words the agent is given and the words the forge holds are one list.
ISSUE_LABELS = [
    LabelSpec(
        name="feature",
        color="a2eeef",
        description="New functionality the user can see: a page, option, capability",
    ),
    LabelSpec(
        name="edit",
        color="bfd4f2",
        description="Refactor or improvement to production code, no feature change",
    ),
    LabelSpec(
        name="chore",
        color="ededed",
        description="No production code: docs, CI, tooling, tests, repo hygiene",
    ),
    LabelSpec(
        name="spike",
        color="d4c5f9",
        description="Investigation or experiment that might not work",
    ),
    LabelSpec(name="bug", color="d73a4a", description="Doesn't behave as expected"),
    LabelSpec(name="S", color="c2e0c6", description="One module, one sitting"),
    LabelSpec(
        name="M",
        color="7fcf8f",
        description="Several modules, or one new adapter or page; one PR",
    ),
    LabelSpec(
        name="L", color="2f9e44", description="Crosses layers; still one reviewable PR"
    ),
    LabelSpec(
        name=EPIC,
        color="5319e7",
        description="Too big for one PR: split into sub-issues, carries no size",
    ),
]


class Identify(BaseModel):
    # How many unidentified issues go on one page.
    batch: Batch = BATCH


# One sub-issue the agent would split an epic into, for the ritual to open.
# Typed and sized in the same breath, so a part is never left behind unidentified.
class Part(BaseModel):
    title: str
    body: str
    kind: Kind
    size: Size


# What the agent read one issue as. A reading and not a report: nothing here
# has happened yet, and `pin` is what puts it on the forge.
class IdentifiedItem(BaseModel):
    number: int
    kind: Kind
    # The size to label it with. None on an epic, which is sized by its parts,
    # and None where the agent would not size it — an issue nobody could
    # size is left unsized rather than guessed at.
    size: Size | None = None
    # Too big for one pull request: the epic label goes on in place of a size.
    epic: bool = False
    # Sub-issues to open under it.
    parts: list[Part] = []
    # Open issues that are already parts of it, to attach rather than reopen.
    children: list[int] = []
    # Issues this one cannot start until they land.
    blocked_by: list[int] = []
    note: str = ""

    # The type, and then a size or the epic label: the labels this reading
    # asks for and no others, so a label the agent did not put on stays on.
    def wanted(self) -> list[str]:
        if self.epic:
            return [self.kind, EPIC]
        return [self.kind, *([self.size] if self.size is not None else [])]


class Identified(BaseModel):
    items: list[IdentifiedItem]


Outcome = Literal["identified", "missed", "stopped"]


# One issue's ending: what was read of it, the sub-issues the ritual opened
# under it, which are numbers only the forge could say, and each write the
# forge refused on it.
class Identification(BaseModel):
    number: int
    outcome: Outcome
    item: IdentifiedItem | None = None
    opened: list[int] = []
    refused: list[str] = []


# What the cast is still to do and what it has done.
class Identifying(Hop):
    project: Project
    batch: Batch = BATCH
    queue: list[Issue] = Field(default_factory=list)
    identified: list[Identification] = Field(default_factory=list)
    # The forge would not list every open issue of yours, so the queue is not
    # the whole backlog. Said in the report, because a cast that cannot see an
    # issue reads exactly like a cast that found nothing to do on it.
    truncated: bool = False
    # Whether the agent has been told to read the skill. Once a cast: every
    # page after the first continues the session that read it.
    briefed: bool = False
    stopped: str = ""

    # The steps that gather, leaf and tally: `pacts/identify.py` names them. A
    # page is read and pinned under classes of its own.
    def to(self, kind: type[_IdentifyingT]) -> _IdentifyingT:
        return self._rebuilt(kind)

    # `None` means "whatever this one had", as every other payload's builder.
    def but(
        self,
        *,
        queue: list[Issue] | None = None,
        identified: list[Identification] | None = None,
        truncated: bool | None = None,
        briefed: bool | None = None,
        stopped: str | None = None,
    ) -> Self:
        update: dict[str, list[Issue] | list[Identification] | bool | str] = {}
        if queue is not None:
            update["queue"] = queue
        if identified is not None:
            update["identified"] = identified
        if truncated is not None:
            update["truncated"] = truncated
        if briefed is not None:
            update["briefed"] = briefed
        if stopped is not None:
            update["stopped"] = stopped
        return self.model_copy(update=update)

    def rowed(self, rows: list[Identification]) -> Self:
        return self.but(identified=[*self.identified, *rows])


# The issues one agent call identifies, and the rest of the cast riding along.
class Page(BaseModel):
    identifying: Identifying
    issues: list[Issue]

    # Every issue on the page rowed as stopped: the page the cast stopped on.
    def stopped(self) -> Identifying:
        return self.identifying.rowed(
            [
                Identification(number=one.number, outcome="stopped")
                for one in self.issues
            ]
        )


# One page read, on its way to the forge: the readings the ritual is about to
# put on, against the page they were read from.
class Pinning(BaseModel):
    page: Page
    items: list[IdentifiedItem]
