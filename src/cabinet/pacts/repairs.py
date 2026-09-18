"""One round of a repair loop: what was run, and what it comes to.

Three loops make the same bargain — run a task, read what it said, and either
move on, give up, or pay for one more attempt. What they measure differs; how
the decision is made does not, so it is made in one place and handed back as
one of the three rulings below.
"""

from pydantic import BaseModel

from cabinet.pacts.project import Project
from cabinet.pacts.tasks import Ran


# What the loop knew when it ran the task, and what the task said.
class Attempt(BaseModel):
    project: Project
    ran: Ran
    # The task that ran: the loop's own gate, or the narrow one that broke
    # last round.
    gate: str
    # The gate the loop owes green before it moves on. Anything else passing
    # is a reason to spend this one, not a reason to move on.
    whole: str
    spent: int
    bound: int
    # Every verdict this run has already given up on, for the loops that carry
    # a memory across branches. Empty is a loop with none.
    seen: list[str] = []
    # The task measures coverage, so a report naming missing lines is a
    # failure however the task exited, and the repair is a test to write.
    covering: bool = False


# Nothing is red. `whole` says the gate that owes green is the one that gave
# this answer, rather than a narrow task on its way there.
class Fixed(BaseModel):
    whole: bool


# Nobody is paying for another attempt: the budget is gone, or this run has
# given up on this verdict once already.
class Stalled(BaseModel):
    reason: str
    seen: list[str]


# One more attempt, with the asking already written. `declined` is the reason
# where the attempt is the operator's to approve and they say no.
class Repair(BaseModel):
    asking: str
    next_gate: str
    seen: list[str]
    declined: str


Ruling = Fixed | Stalled | Repair
