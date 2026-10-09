"""How much one turn of a loop may take, and what it has taken so far.

Every repair loop counts the same way: a step may be retried up to the bound,
going green hands the count back, and a payload that dies takes its counts
with it. The rule lives here so the loops cannot drift into two dialects of it.
The batch is the other half of the same question — how much of a queue one
round takes — and it is here rather than in either domain's own pact because
threads and issues both take their queues in rounds and neither owns the
other's number. What a cast has spoken for out of the engine's step budget is
the same count at the scale of a whole cast, and a sweep and `review` both
keep it.
"""

from typing import Annotated, Self

from pydantic import BaseModel, Field

# How much one round takes before the next one asks what is left: open threads
# for `review`, unidentified issues for `identify`. Forty at once is one reading
# nobody holds in their head and one agent asked to do forty things before
# anything lands. No ceiling: a batch bigger than the queue is the whole queue.
Batch = Annotated[int, Field(ge=1)]
# Spelled once, so the flag's default is one number and not four.
BATCH = 7


class Reserving(BaseModel):
    # Steps the cast has spoken for out of the engine's budget: every step that
    # works no branch, counted once the queue is known, and the worst each
    # branch it took can spend.
    reserved: int = 0

    def spoke_for(self, steps: int) -> Self:
        update: dict[str, int] = {"reserved": self.reserved + steps}
        return self.model_copy(update=update)


class Budgeted(BaseModel):
    # Keyed by step name, so two loops on one branch never spend each other's
    # attempts.
    budgets: dict[str, int] = {}

    def spent(self, name: str) -> int:
        return self.budgets.get(name, 0)

    # Every attempt this payload has paid for, whichever step spent it: what
    # the operator is asked about is the next attempt on this branch, not the
    # next attempt at one step of it. Summed rather than listed by name, so a
    # loop added later counts itself.
    def attempts(self) -> int:
        return sum(self.budgets.values())

    def charged(self, name: str) -> Self:
        return self._budgeted({**self.budgets, name: self.spent(name) + 1})

    # A step that goes green hands its budget back, so a step reached a second
    # time on the same branch starts over rather than inheriting what the
    # first pass spent.
    def cleared(self, name: str) -> Self:
        kept = {step: count for step, count in self.budgets.items() if step != name}
        return self._budgeted(kept)

    # Typed on the way in: a bare literal handed to `model_copy` is read as
    # `dict[str, Any]`, which the checker here refuses.
    def _budgeted(self, budgets: dict[str, int]) -> Self:
        update: dict[str, dict[str, int]] = {"budgets": budgets}
        return self.model_copy(update=update)
