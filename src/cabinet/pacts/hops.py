"""A payload is the step it goes to.

vekna routes a returned payload to the one step that takes its exact class, so
each step has a class of its own. Those classes add no fields to what they
carry: a sweep step's is a `Work` by another name, and the next hop is the
same fields rebuilt under the next step's class.
"""

from typing import TypeVar

from pydantic import BaseModel, ConfigDict

_HopT = TypeVar("_HopT", bound="Hop")


class Hop(BaseModel):
    # A step's class is where a payload is going, not what it is: held in a
    # field — `Triage.branch`, `Closed.work` — it is rebuilt as the field's
    # own class, so nothing downstream carries a stale destination.
    model_config = ConfigDict(revalidate_instances="subclass-instances")

    # Through JSON, so the result is exactly `kind` whatever class `self` is:
    # the engine reads the exact class, and a subclass is another step.
    def to(self, kind: type[_HopT]) -> _HopT:
        return kind.model_validate_json(self.model_dump_json())
