"""Heal your pull requests: each one taken as far as its tasks go.

    vekna cast heal.mine [--plan-only true] [--bound N] [--batch N]
    vekna cast heal.this [--plan-only true] [--bound N] [--batch N]
    vekna cast heal.pr --number N [--plan-only true] [--bound N] [--batch N]
    vekna cast heal.main [--plan-only true] [--bound N]
    vekna cast merge [--plan-only true] [--bound N]
    vekna cast ci [--plan-only true] [--bound N]
    vekna cast answer [--plan-only true] [--bound N] [--batch N]
    vekna cast review [--plan-only true]
    vekna cast guide [--plan-only true]

``heal.mine`` surveys every open pull request of yours not wearing the wait
label, oldest-modified first, and works none of them itself: each one with
work goes to a ``heal.pr`` of its own, queued on the daemon, which runs it in
a pooled worktree beside the others, and the cast stays until they end and
reports their rows. With no daemon listening it says so and
fails. ``heal.pr`` takes the pull request it is given the number of;
``heal.this`` and the task rituals take the pull request of the branch at the
cwd. A task ritual is ``heal.this`` that may work one task and no other.

``heal.main`` takes no pull request: it reads the configured CI jobs on the
base. Where one is red and no fix of yours is open, it cuts
``main_fix_branch`` from the base as the remote has it, fixes each red job
the way the ci task does, without the rerun, pushes, and opens a pull
request. A branch its gate will not go green on is opened all the same, and
the pull request says what stopped it. Where nothing was committed, nothing
is opened.

Each pull request is surveyed first: whether it conflicts with its base, which
of the configured CI jobs are red, how many review threads are open, and which
labels it wears. That becomes its todo list, in the order a cast works it:
merge, ci, answer, review, guide. Facts make a todo; the reviewed and qa labels
only take one away. The list is printed a line per pull request as it is read.
With ``--plan-only true`` that is all: no checkout, no commit, no label.

Otherwise a branch with a task this cast works is taken: the worktree must be
clean, the remote is fetched, and the branch is checked out and fast-forwarded
to it. The base is only ever read as the remote has it: a pooled worktree
cannot stand on a base the tree it was made from is standing on. Then
``tend`` hands the branch each task in turn, and every task ends back at
``tend``:

- **merge**, only where the branch conflicts: the base is merged in, an agent
  resolves the conflicts, and the gate is made green before the merge is
  committed. A branch the gate will not go green on stands down: the worktree
  is released and the rest of its tasks are worked anyway.
- **ci**, one red check at a time, for the configured jobs: where a job has
  ``rerun`` and has not been rerun on this head, it runs again, and the task
  ends there for the next cast to read. Otherwise an agent reads the job's log
  and fixes it; a job with a ``gate`` then goes round the repair loop against
  it, ``fast`` between rounds, and one without is committed as the agent left
  it. A ``covering`` job's gap is measured here and covered with tests. Each
  job's fix is a commit of its own, and a job gets one check fixed per cast
  however many of its matrix entries are red. A job that stands the branch
  down ends the task, and the checks behind it are named. A fix that changes
  nothing leaves its job red, and the row says it passes here. A branch whose
  merge was committed leaves ci for the next cast: the push starts a run of
  its own.
- **answer**, attended only: an unattended cast leaves the threads for you and
  says how many wait. First whatever an earlier cast's forge failure left
  half-settled is finished. Then the open threads go in batches of
  ``--batch``: an agent reads them against the code into a triage, you answer
  each item in your own words (saying nothing takes the reading's proposal),
  and another agent fixes what you said to fix and drafts every reply. The
  ritual opens the issues you said to file, posts the replies and settles the
  threads, and reads what is still open for the next round, up to three. What
  the answers changed goes through the gate and is committed. A round that
  finds nothing open puts the answered label on; the next answer task takes
  it off before it starts.
- **review**: the quality review, as inline comments, then the reviewed label.
  Whatever this cast committed is pushed first, so the comments anchor to code
  the forge has.
- **guide**, only once nothing else is left: an agent follows the smoke-test
  skill and writes the manual check for the branch, which goes up as a plain
  comment, then the qa label. A comment an earlier guide left is edited in
  place: take the label off to ask for another.

What a cast committed and has not pushed goes up before the branch is left.
Nothing waits for CI after a push, and nothing merges a branch that is merely
behind.

Neither the gate nor the coverage is re-run whole while a repair is underway.
Where the runner names the task that broke, the next round runs that task
alone, and the gate itself runs once more when it comes back green.

A branch is left alone rather than reported broken when the checkout will not
go through, which is what another worktree standing on it looks like. A fetch
that fails is not the same thing, so that one ends the cast.

Two things end the whole cast rather than one branch: a worktree that is not
clean, and an agent that dies mid-flight. Both still print the report first,
then fail the cast.

Budgets are per step and per branch: a step may be retried ``--bound`` times,
going green clears its count, and moving to the next pull request clears them
all. A verdict a step already gave up on once is not paid for twice: the next
branch of the same cast whose gate says the same thing stands down without
spending its budget. Each ``heal.pr`` is a cast of its own, and pays once.
A cast is attended unless vekna was told ``--unattended``.
The budgets decide every repair either way. Attended, the review threads are
put to you, the one question a cast asks.

A branch is taken only where the worst it can spend still fits the engine's
step budget; one that does not ends the cast without failing it, and the report
names what was not reached.
"""

from cabinet.gates.ritual.vekna.heal.answer import (
    answer_gate,
    answer_threads,
    ask_triage,
    land_answers,
    post_answers,
    read_threads,
    settle_left,
)
from cabinet.gates.ritual.vekna.heal.branch import (
    check_clean,
    finish_pr,
    open_pull,
    push_work,
    set_aside,
    skip_pr,
    stand_down,
    sync_branch,
    tend,
)
from cabinet.gates.ritual.vekna.heal.cast import (
    attend,
    chart,
    muster_main,
    muster_mine,
    muster_pr,
    muster_this,
    mustered,
    summon,
    survey,
)
from cabinet.gates.ritual.vekna.heal.ci import (
    close_gap,
    job_gate,
    land_job,
    mend_job,
    pick_job,
    rerun_jobs,
)
from cabinet.gates.ritual.vekna.heal.guide import post_guide
from cabinet.gates.ritual.vekna.heal.merge import (
    finish_merge,
    gate_check,
    merge_base,
    resolve_conflicts,
)
from cabinet.gates.ritual.vekna.heal.review import quality_review

__all__ = [
    "answer_gate",
    "answer_threads",
    "ask_triage",
    "attend",
    "chart",
    "check_clean",
    "close_gap",
    "finish_merge",
    "finish_pr",
    "gate_check",
    "job_gate",
    "land_answers",
    "land_job",
    "mend_job",
    "merge_base",
    "muster_main",
    "muster_mine",
    "muster_pr",
    "muster_this",
    "mustered",
    "open_pull",
    "pick_job",
    "post_answers",
    "post_guide",
    "push_work",
    "quality_review",
    "read_threads",
    "rerun_jobs",
    "resolve_conflicts",
    "set_aside",
    "settle_left",
    "skip_pr",
    "stand_down",
    "summon",
    "survey",
    "sync_branch",
    "tend",
]
