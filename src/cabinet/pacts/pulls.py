"""What a sweep carries, branch by branch, and what it leaves behind."""

from typing import Annotated, Literal

from pydantic import BaseModel, Field

from cabinet.pacts.project import Project

# A bound counts attempts at one step, so zero would mean a step that may never
# be tried at all; past five a repair loop has stopped being a repair loop.
Bound = Annotated[int, Field(ge=1, le=5)]


class PrSweep(BaseModel):
    bound: Bound = 3


# Which pass a cast is. The two share every step that takes a branch and writes
# a row; they part at the gate — the fast pass merges and makes the gate green,
# the slow one measures coverage and writes the tests.
Mode = Literal["refresh", "cover"]


# One pull request as the forge lists it, in the rituals' own words: which
# forge spelled the fields is the adapter's business.
class PullRequest(BaseModel):
    number: int
    title: str
    url: str
    branch: str
    base: str
    updated_at: str
    # As they stood at the listing. Only the wait label is read from here, and
    # only once: everything later asks the forge again, because a ritual adds
    # labels of its own as it goes.
    labels: list[str] = []

    def wears(self, label: str) -> bool:
        return label in self.labels


# What CI says about one thing it ran. `passed` is None while a run is still
# going, which is why nothing reads it as anything but "not success yet".
# `title` is the one-line summary a job writes for itself: absent for most of
# the board, and for the patch check the coverage this branch achieved — the
# number the slow pass would otherwise have to read out of prose.
class Check(BaseModel):
    name: str
    passed: bool | None = None
    title: str = ""


class Board(BaseModel):
    checks: list[Check] = []
    # A page that stopped short of the whole board. What fell off the end could
    # be the check either reader turns on, and a page that does not say is not
    # a page saying yes.
    truncated: bool = False


Outcome = Literal["green", "blocked", "skipped"]


class Checked(BaseModel):
    number: int
    branch: str
    url: str
    # What the night can say about the branch: whether the gates went green and
    # the work went up. `skipped` is neither — the branch was never taken.
    outcome: Outcome
    # None when git could not say. Nothing to push and "we could not tell" are
    # different answers, and the report prints them differently.
    unpushed: int | None
    note: str = ""


# A note grows by joining rather than replacing, so no half of it writes over
# another's. The separator is decided here and nowhere else.
def joined(*parts: str) -> str:
    return "; ".join(part for part in parts if part)


# Every step carries this, because the report is owed however the cast ends.
class Run(BaseModel):
    project: Project
    bound: int
    mode: Mode = "refresh"
    queue: list[PullRequest] = []
    checked: list[Checked] = []
    stopped: str = ""
    # Every verdict a gate on this run has given up on, carried across branches
    # so the next one can recognise it: a night where the same thing is broken
    # everywhere should pay for that answer once, not once per pull request.
    seen: list[str] = []

    # Every step routes state forward by building the next payload from the
    # last, and `model_copy` takes an untyped mapping — so the field list is
    # spelled here once, typed, and `None` means "whatever this one had".
    def but(
        self,
        *,
        queue: list[PullRequest] | None = None,
        checked: list[Checked] | None = None,
        stopped: str | None = None,
        seen: list[str] | None = None,
    ) -> Run:
        update: dict[str, list[PullRequest] | list[Checked] | list[str] | str] = {}
        if queue is not None:
            update["queue"] = queue
        if checked is not None:
            update["checked"] = checked
        if stopped is not None:
            update["stopped"] = stopped
        if seen is not None:
            update["seen"] = seen
        return self.model_copy(update=update)

    def rowed(self, row: Checked) -> Run:
        return self.but(checked=[*self.checked, row])


# `budgets` dies with this payload, which is what "a branch change clears all
# budgets" means — a fresh Work is built per pull request and inherits nothing.
class Work(BaseModel):
    run: Run
    pr: PullRequest
    budgets: dict[str, int] = {}
    merging: bool = False
    # What the repair loop should run next, empty for the step's own gate: the
    # narrow task named when the gate broke, so an agent's attempt is judged by
    # the thing that was wrong rather than by the whole chain in front of it.
    gate: str = ""
    # The merge brought nothing in, so the tree is the one CI has already
    # graded. Only ever true before any agent has touched the branch.
    unchanged: bool = False
    note: str = ""
    # What stopped this branch, in the words of whatever stopped it. Written
    # once, by the step that gave up, and never written over: read by the
    # review agent, which is told not to raise it, and by the morning, which
    # is told it first.
    reason: str = ""
    # This branch will not be made green tonight, and is being read anyway.
    blocked: bool = False

    # The fields a step routes forward on its way through a branch. The flags
    # each have a builder of their own below, named for the decision they
    # record rather than the field they set.
    def but(
        self,
        *,
        run: Run | None = None,
        budgets: dict[str, int] | None = None,
        gate: str | None = None,
        note: str | None = None,
    ) -> Work:
        update: dict[str, Run | dict[str, int] | str] = {}
        if run is not None:
            update["run"] = run
        if budgets is not None:
            update["budgets"] = budgets
        if gate is not None:
            update["gate"] = gate
        if note is not None:
            update["note"] = note
        return self.model_copy(update=update)

    # The merge brought nothing in, or it did.
    def graded(self, *, unchanged: bool) -> Work:
        return self._flagged({"unchanged": unchanged})

    # The merge stopped, and this is what git said about it.
    def merging_on(self, note: str) -> Work:
        return self._flagged({"merging": True, "note": note})

    def merged(self) -> Work:
        return self._flagged({"merging": False})

    # The step that gives up on the branch says why, once.
    def stopped_by(self, reason: str) -> Work:
        return self._flagged({"reason": reason})

    # The worktree is released and the branch is read anyway.
    def standing_down(self, note: str) -> Work:
        return self._flagged({"blocked": True, "note": note})

    # Typed on the way in: a bare literal handed to `model_copy` is read as
    # `dict[str, Any]`, which the checker here refuses.
    def _flagged(self, update: dict[str, bool | str]) -> Work:
        return self.model_copy(update=update)

    # --- budgets ---------------------------------------------------------

    def spent(self, name: str) -> int:
        return self.budgets.get(name, 0)

    def exhausted(self, name: str) -> bool:
        return self.spent(name) >= self.run.bound

    def charged(self, name: str) -> Work:
        return self.but(budgets={**self.budgets, name: self.spent(name) + 1})

    # A step that goes green hands its budget back, so a step reached a second
    # time on the same branch starts over rather than inheriting what the
    # first pass spent.
    def cleared(self, name: str) -> Work:
        kept = {step: count for step, count in self.budgets.items() if step != name}
        return self.but(budgets=kept)

    # --- endings ---------------------------------------------------------

    # Why the branch stopped comes first, which is the order the morning wants
    # it in. Every ending goes through here, so no ending can write over
    # another's half.
    def telling(self, *extra: str) -> str:
        return joined(self.reason, self.note, *extra)

    def checked(self, outcome: Outcome, *, unpushed: int | None, note: str) -> Checked:
        return Checked(
            number=self.pr.number,
            branch=self.pr.branch,
            url=self.pr.url,
            outcome=outcome,
            unpushed=unpushed,
            note=note,
        )

    # The run gives up with a pull request in flight: it goes into the report
    # as blocked, because the branch is left wherever the failure left it.
    def abandoned(self, reason: str) -> Run:
        row = self.checked("blocked", unpushed=None, note=f"left mid-flight: {reason}")
        return self.run.rowed(row).but(stopped=reason)


class Closed(BaseModel):
    work: Work
    outcome: Literal["green", "blocked"]


# What the night did, branch by branch, and nothing sorted into work lists on
# top: this pass refreshes pull requests, it does not triage them.
class Report(BaseModel):
    checked: list[Checked] = []
    not_reached: list[str] = []
    failed: str = ""
