"""What a step is allowed to spend on one branch, counted per step.

Every repair loop counts the same way: a step may be retried up to the bound,
going green hands the count back, and a payload that dies takes its counts
with it. The rule lives here so the loops cannot drift into two dialects of it.
"""

from typing import Self

from pydantic import BaseModel


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
