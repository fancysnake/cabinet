"""The repair loop every heal task with a gate goes round.

Neither the gate nor the coverage is re-run whole while a repair is underway.
Where the runner names the task that broke, the next round runs that task
alone, and the gate itself runs once more when it comes back green.

Budgets are per step and per branch: a step may be retried ``--bound`` times,
going green clears its count, and moving to the next pull request clears them
all. A verdict a step already gave up on once is not paid for twice: the next
branch of the same cast whose gate says the same thing stands down without
spending its budget. Each ``heal.pr`` is a cast of its own, and pays once. The
budgets decide every repair, attended or not.
"""

from typing import TypeVar

from cabinet.gates.ritual.vekna.heal.agents import asked
from cabinet.pacts.heal import Chart, StandDown
from cabinet.pacts.healing import Work
from cabinet.pacts.project import CiJob
from cabinet.pacts.repairs import Attempt, Fixed, Stalled
from cabinet.pacts.services import services

_WorkT = TypeVar("_WorkT", bound=Work)
_NextT = TypeVar("_NextT", bound=Work)


# A branch this cast has stopped paying for, carrying whatever the round
# learned into the cast's memory: the next branch broken the same way stands
# down without spending a budget of its own.
def _gave_up(work: Work, reason: str, seen: list[str]) -> Work:
    return work.stopped_by(reason).but(run=work.run.but(seen=seen))


# One round of a repair loop, shared by every loop that runs a gate, against
# the commands `against` names as a CI job would. The branch comes back
# charged and pointed at what to run next, or green and sent on to `then`, or
# given up on. `work.gate` is the task that broke last time round, where the
# runner named one: an agent working on one linter is judged by that linter,
# not by the whole chain in front of it.
async def repaired(
    work: _WorkT, against: CiJob, *, name: str, then: type[_NextT]
) -> _NextT | _WorkT | StandDown | Chart:
    project = work.run.project
    gate = work.gate or against.gate
    ran = await services().tasks(project).run(gate)
    ruling = services().repairs.ruling(
        Attempt(
            project=project,
            ran=ran,
            gate=gate,
            whole=against.gate,
            fast=against.fast,
            spent=work.spent(name),
            bound=work.run.bound,
            seen=work.run.seen,
            covering=against.covering,
        )
    )
    if isinstance(ruling, Fixed):
        # A task passing on its own is not the gate passing — it is the
        # reason to spend the gate. The whole chain runs once more.
        if not ruling.whole:
            return work.but(gate="")
        return work.but(gate="").cleared(name).to(then)
    if isinstance(ruling, Stalled):
        return _gave_up(work, ruling.reason, ruling.seen).to(StandDown)
    escalated = services().sizes.escalates(red=len(work.red), spent=work.spent(name))
    if fallen := await asked(
        work, ruling.asking, key=name, escalated=escalated, skills=ruling.skills
    ):
        return work.abandoned(fallen.reason).to(Chart)
    return work.but(gate=ruling.next_gate).charged(name)
