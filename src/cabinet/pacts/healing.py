"""What a heal cast carries, branch by branch, and what it leaves behind."""

from typing import Literal, Self, TypeAlias, TypeVar, get_args

from pydantic import BaseModel, Field

from cabinet.pacts.budgets import BATCH, Batch, Budgeted, Reserving
from cabinet.pacts.hops import Hop
from cabinet.pacts.project import Project
from cabinet.pacts.pulls import Board, Bound, Check, PullRequest
from cabinet.pacts.threads import Thread

_RunT = TypeVar("_RunT", bound="Run")
_WorkT = TypeVar("_WorkT", bound="Work")

# What a branch may need next, in the order a cast does it: the base merged
# in, CI made green, the threads answered, a review posted, the guide posted:
# the smoke-test instructions, as a comment.
Todo = Literal["merge", "ci", "answer", "review", "guide"]

# The todos the graph has steps for, in the same order. A todo outside it is
# surveyed and reported, and nothing works it.
Task = Literal["merge", "ci", "answer", "review"]
TASKS: tuple[Task, ...] = get_args(Task)


def _tasks() -> list[Task]:
    return list(TASKS)


class Heal(BaseModel):
    # Survey, say what each branch needs, and change nothing: a cast that may
    # work no task.
    plan_only: bool = False
    bound: Bound = 3
    # Somebody is at the terminal: an agent runs in Claude's `auto` permission
    # mode instead of refusing everything outside its allowlist, and another
    # repair attempt is asked for rather than spent on the budget's say-so.
    attended: bool = False
    # How many open threads one round of `answer` reads, answers and settles
    # before the next round fetches what the forge still holds open.
    batch: Batch = BATCH

    # The tasks a cast may work: the ones named, every one where none is, and
    # none at all for a plan.
    def working(self, *tasks: Task) -> list[Task]:
        return [] if self.plan_only else list(tasks or TASKS)


# Everything the survey reads about one pull request, read once.
class Facts(BaseModel):
    pull: PullRequest
    board: Board
    threads: list[Thread]
    # The forge's answer where it had one, git's where it did not.
    conflicted: bool


# What the survey made of one pull request.
class Surveyed(BaseModel):
    number: int
    branch: str
    url: str
    todos: list[Todo]
    # The configured CI jobs whose checks are red, and the open threads: what
    # `ci` and `answer` would work through.
    red: list[Check]
    threads: int


# A pull request the forge or git would not answer about, and what it said.
# No todos, because none were read.
class Unsurveyed(BaseModel):
    number: int
    branch: str
    url: str
    note: str


Outcome = Literal["worked", "blocked", "skipped"]


class Checked(BaseModel):
    number: int
    branch: str
    url: str
    # Whether the branch's tasks were worked through, or it was given up on.
    # `worked` says nothing of the gate, which only merge, ci and answer run.
    # `skipped` is neither: the branch was never taken.
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
class Run(Reserving, Hop):
    project: Project
    bound: Bound = 3
    attended: bool = False
    batch: Batch = BATCH
    # Which tasks this cast may work: every one for `heal`, one for a task
    # ritual, none for a plan. The survey still says everything a branch needs.
    tasks: list[Task] = Field(default_factory=_tasks)
    queue: list[PullRequest] = Field(default_factory=list)
    surveyed: list[Surveyed | Unsurveyed] = Field(default_factory=list)
    checked: list[Checked] = Field(default_factory=list)
    stopped: str = ""
    # Every verdict a gate on this cast has given up on, carried across
    # branches so the next one can recognise it: a cast where the same thing
    # is broken everywhere should pay for that answer once, not once per pull
    # request.
    seen: list[str] = Field(default_factory=list)

    # The cast's own steps and no others: `pacts/heal.py` names one class per
    # step, and the ones that take a branch are `Work`'s, not these.
    def to(self, kind: type[_RunT]) -> _RunT:
        return self._rebuilt(kind)

    # Every step routes state forward by building the next payload from the
    # last, and `model_copy` takes an untyped mapping — so the field list is
    # spelled here once, typed, and `None` means "whatever this one had".
    def but(
        self,
        *,
        queue: list[PullRequest] | None = None,
        surveyed: list[Surveyed | Unsurveyed] | None = None,
        checked: list[Checked] | None = None,
        stopped: str | None = None,
        seen: list[str] | None = None,
    ) -> Self:
        update: dict[
            str,
            list[PullRequest]
            | list[Surveyed | Unsurveyed]
            | list[Checked]
            | list[str]
            | str,
        ] = {}
        if queue is not None:
            update["queue"] = queue
        if surveyed is not None:
            update["surveyed"] = surveyed
        if checked is not None:
            update["checked"] = checked
        if stopped is not None:
            update["stopped"] = stopped
        if seen is not None:
            update["seen"] = seen
        return self.model_copy(update=update)

    # The head of the queue taken off it, its row added.
    def took(self, row: Surveyed | Unsurveyed) -> Self:
        return self.but(queue=self.queue[1:], surveyed=[*self.surveyed, row])

    # What of `todos` this cast may work, in the order it works them. Never
    # `answer` with nobody at the terminal: every item of a triage is yours to
    # decide, and the threads wait for a cast you attend.
    def worked(self, todos: list[Todo]) -> list[Task]:
        return [
            task
            for task in self.tasks
            if task in todos and (task != "answer" or self.attended)
        ]

    # The surveyed pull requests whose threads this cast could have answered
    # and left for you, because nobody was there to decide them.
    def waiting(self) -> list[Surveyed]:
        if self.attended or "answer" not in self.tasks:
            return []
        return [
            row
            for row in self.surveyed
            if isinstance(row, Surveyed) and "answer" in row.todos
        ]

    # `pull` taken with the tasks it will get and the red checks `ci` works
    # through, and the worst it can spend spoken for. A fresh `Work` per pull
    # request, so no budget survives the branch change.
    def take(self, row: Surveyed, pull: PullRequest, steps: int) -> "Work":
        todos = self.worked(row.todos)
        return Work(run=self.spoke_for(steps), pr=pull, todos=todos, red=row.red)

    def rowed(self, row: Checked) -> Self:
        return self.but(checked=[*self.checked, row])


# Every field a step may route forward, in one annotation, so the copy that
# carries them can be one method.
_Update: TypeAlias = dict[
    str, Run | dict[str, int] | list[Task] | list[Check] | bool | str
]


# `budgets` dies with this payload, which is what "a branch change clears all
# budgets" means — a fresh Work is built per pull request and inherits nothing.
class Work(Budgeted, Hop):
    run: Run
    pr: PullRequest
    # The tasks still to work on this branch, the next one first.
    todos: list[Task] = Field(default_factory=list)
    # The red checks `ci` has still to work, the one in hand first.
    red: list[Check] = Field(default_factory=list)
    merging: bool = False
    # What the repair loop should run next, empty for the step's own gate: the
    # narrow task named when the gate broke, so an agent's attempt is judged by
    # the thing that was wrong rather than by the whole chain in front of it.
    gate: str = ""
    # This cast committed on the branch since it last pushed.
    changed: bool = False
    note: str = ""
    # What stopped this branch, in the words of whatever stopped it. Written
    # once, by the step that gave up, and never written over: read by the
    # review agent, which is told not to raise it, and by the report, which
    # tells it first.
    reason: str = ""

    # This branch's gate will not be made green by this cast, and the rest of
    # its tasks are worked anyway: only a step that gives up says why.
    @property
    def blocked(self) -> bool:
        return bool(self.reason)

    # The steps that take a branch, and no others: ending a branch means
    # routing the `Run` this carries, which has a `to` of its own.
    def to(self, kind: type[_WorkT]) -> _WorkT:
        return self._rebuilt(kind)

    # The fields a step routes forward on its way through a branch, with
    # `None` meaning "whatever this one had". The flags each have a builder of
    # their own below, named for the decision they record rather than the
    # field they set — and every one of them, this included, copies through
    # `_copied`.
    def but(
        self,
        *,
        run: Run | None = None,
        budgets: dict[str, int] | None = None,
        todos: list[Task] | None = None,
        gate: str | None = None,
        note: str | None = None,
    ) -> Self:
        update: _Update = {}
        if run is not None:
            update["run"] = run
        if budgets is not None:
            update["budgets"] = budgets
        if todos is not None:
            update["todos"] = todos
        if gate is not None:
            update["gate"] = gate
        if note is not None:
            update["note"] = note
        return self._copied(update)

    # The merge stopped, and this is what git said about it.
    def merging_on(self, note: str) -> Self:
        return self._copied({"merging": True, "note": note})

    # The merge is closed and committed: there is something to push.
    def merged(self) -> Self:
        return self._copied({"merging": False, "changed": True})

    # The check in hand is done with, and what fixed it is committed.
    def landed(self) -> Self:
        return self._copied({"red": self.red[1:], "changed": True})

    # The check in hand is left red, and this says why.
    def passed_over(self, note: str) -> Self:
        return self._copied({"red": self.red[1:], "note": joined(self.note, note)})

    # The answers are committed: there is something to push.
    def committed(self) -> Self:
        return self._copied({"changed": True})

    def pushed(self) -> Self:
        return self._copied({"changed": False})

    # The step that gives up on the branch says why, once.
    def stopped_by(self, reason: str) -> Self:
        return self._copied({"reason": reason})

    # The worktree is released and the rest of the tasks are worked anyway.
    # Whatever the merge had already committed is still to push.
    def standing_down(self, note: str) -> Self:
        return self._copied({"changed": True, "note": note})

    # The one way a `Work` is copied. Typed on the way in: a bare literal
    # handed to `model_copy` is read as `dict[str, Any]`, which the checker
    # here refuses.
    def _copied(self, update: _Update) -> Self:
        return self.model_copy(update=update)

    # --- budgets ---------------------------------------------------------

    # The counting is `Budgeted`'s, shared with every other loop; what a
    # branch adds is the bound, which lives on the run.
    def exhausted(self, name: str) -> bool:
        return self.spent(name) >= self.run.bound

    # --- endings ---------------------------------------------------------

    # Why the branch stopped comes first, which is the order the report wants
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

    # The cast gives up with a pull request in flight: it goes into the report
    # as blocked, because the branch is left wherever the failure left it.
    def abandoned(self, reason: str) -> Run:
        row = self.checked("blocked", unpushed=None, note=f"left mid-flight: {reason}")
        return self.run.rowed(row).but(stopped=reason)


# What the cast came to: every pull request's survey, what became of each
# branch it worked, and what it never reached.
class Healed(BaseModel):
    surveyed: list[Surveyed | Unsurveyed] = []
    checked: list[Checked] = []
    not_reached: list[str] = []
