"""Heal your pull requests: each one taken as far as its tasks go.

    vekna cast heal.mine [--plan-only true] [--bound N] [--attended false] [--batch N]
    vekna cast heal.this [--plan-only true] [--bound N] [--attended false] [--batch N]
    vekna cast heal.pr --number N [--plan-only true] [--bound N] [--batch N]
    vekna cast merge [--plan-only true] [--bound N] [--attended false]
    vekna cast ci [--plan-only true] [--bound N] [--attended false]
    vekna cast answer [--plan-only true] [--bound N] [--batch N]
    vekna cast review [--plan-only true] [--attended false]
    vekna cast guide [--plan-only true] [--attended false]

``heal.mine`` surveys every open pull request of yours not wearing the wait
label, oldest-modified first, and works none of them itself: each one with
work goes to a ``heal.pr`` of its own, queued on the daemon, which runs it in
a pooled worktree beside the others. With no daemon listening it says so and
fails. ``heal.pr`` takes the pull request it is given the number of;
``heal.this`` and the task rituals take the pull request of the branch at the
cwd. A task ritual is ``heal.this`` that may work one task and no other.

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
A cast is attended unless vekna was told ``--unattended`` or the ritual
``--attended false``, which ``[defaults."cabinet:<ritual>"]`` can set per
repository.
Unattended, nothing is asked and the budgets decide; attended, each repair
attempt is put to you first.

A branch is taken only where the worst it can spend still fits the engine's
step budget; one that does not ends the cast without failing it, and the report
names what was not reached.
"""

from typing import TypeAlias, TypeVar

from vekna.folio.flow import decide, enqueue
from vekna.lexicon import Done, NoDaemonError, RitualError, attended, emit_delta, step

from cabinet.pacts.agent import Fallen, Misread
from cabinet.pacts.budgets import ROUNDS
from cabinet.pacts.forge import ForgeError, ForgeProtocol
from cabinet.pacts.guide import GUIDE_MARK, Guide
from cabinet.pacts.heal import (
    AnswerGate,
    AnswerThreads,
    AskTriage,
    Chart,
    CheckClean,
    CloseGap,
    FinishMerge,
    FinishPr,
    GateCheck,
    JobGate,
    LandAnswers,
    LandJob,
    MendJob,
    MergeBase,
    MusterMine,
    MusterPr,
    MusterThis,
    PickJob,
    PostAnswers,
    PostGuide,
    PushWork,
    QualityReview,
    ReadThreads,
    RerunJobs,
    ResolveConflicts,
    SetAside,
    SettleLeft,
    SkipPr,
    StandDown,
    Summon,
    Survey,
    SyncBranch,
    Tally,
    Tend,
)
from cabinet.pacts.healing import (
    Facts,
    Heal,
    Healed,
    HealPr,
    Queued,
    Run,
    Surveyed,
    Task,
    Unsurveyed,
    Work,
)
from cabinet.pacts.issues import Listing
from cabinet.pacts.project import CiJob, Project
from cabinet.pacts.pulls import PullRequest
from cabinet.pacts.repairs import Attempt, Fixed, Stalled
from cabinet.pacts.scm import ScmError
from cabinet.pacts.services import services
from cabinet.pacts.threads import (
    Answered,
    Finding,
    Findings,
    Thread,
    TriageNotes,
    filed_as,
    filed_for,
    signed,
)

_RunT = TypeVar("_RunT", bound=Run)
_WorkT = TypeVar("_WorkT", bound=Work)
_NextT = TypeVar("_NextT", bound=Work)

# --- the cast --------------------------------------------------------------


# What every heal ritual's body makes of its components: the first step's
# payload, working `tasks`, or every task where none is named. vekna's
# `--unattended` has the last word, so `attended` only ever turns a cast down.
def mustered(kind: type[_RunT], components: Heal, *tasks: Task) -> _RunT:
    return kind(
        project=services().project(),
        bound=components.bound,
        attended=attended() and components.attended,
        batch=components.batch,
        tasks=components.working(*tasks),
    )


# Before the first fetch: an ssh remote would ask for a passphrase on a
# terminal no command under a cast has, and the answer is a config line.
async def _listed(run: Run) -> list[PullRequest]:
    await services().scm(run.project).preflight()
    return await services().forge(run.project).pulls()


# Queued, with every step that works no branch spoken for now that the queue
# is known.
def _queued(run: Run, queue: list[PullRequest], kind: type[_RunT]) -> _RunT:
    opening = services().steps.opening(len(queue))
    return run.but(queue=queue).spoke_for(opening).to(kind)


# Every open pull request of yours the forge lists, bar the parked ones.
@step
async def muster_mine(run: MusterMine) -> Tally | Summon:
    try:
        pulls = await _listed(run)
    except (ScmError, ForgeError) as error:
        return run.but(stopped=str(error)).to(Tally)
    return _queued(run, services().pulls.wanted(pulls, run.project), Summon)


# The open pull request of yours for the branch at the cwd.
@step
async def muster_this(run: MusterThis) -> Chart | Survey:
    try:
        pulls = await _listed(run)
        here = await services().scm(run.project).here()
    except (ScmError, ForgeError) as error:
        return run.but(stopped=str(error)).to(Chart)
    if not (queue := services().pulls.at(pulls, here)):
        stopped = f"no open pull request of yours has {here} as its branch"
        return run.but(stopped=stopped).to(Chart)
    return _queued(run, queue, Survey)


# The open pull request of yours `heal.mine` queued this cast for. Surveyed
# again rather than trusted from the parent: the queue may have held this
# cast for a while, and the facts decide.
@step
async def muster_pr(mustering: MusterPr) -> Chart | Survey:
    run = mustering.run
    try:
        pulls = await _listed(run)
    except (ScmError, ForgeError) as error:
        return run.but(stopped=str(error)).to(Chart)
    if not (queue := services().pulls.numbered(pulls, mustering.number)):
        stopped = f"no open pull request of yours is #{mustering.number}"
        return run.but(stopped=stopped).to(Chart)
    return _queued(run, queue, Survey)


# Read the next pull request's facts, say what it needs, and take it where
# this cast works any of that.
@step
async def survey(run: Survey) -> Chart | Survey | CheckClean:
    if not run.queue:
        return run.to(Chart)
    # Asked before the survey rather than after: a branch the budget has no
    # room for is left for the next cast, unread. Not a failure, and the
    # report names it; running out of the engine's budget instead would raise
    # past `chart` with a branch half-merged.
    # A plan works no task, so it takes no branch and has no share to ask for.
    if (share := services().steps.heal_share(run) if run.tasks else 0) is None:
        return run.to(Chart)
    pull = run.queue[0]
    row = await _surveyed(run.project, pull)
    emit_delta(services().report.surveyed(row))
    after = run.took(row)
    if isinstance(row, Unsurveyed) or not after.worked(row.todos):
        return after.to(Survey)
    return after.take(row, pull, share).to(CheckClean)


# `heal.mine`'s survey: read the next pull request's facts, say what it
# needs, and hand it to a `heal.pr` of its own where any of that is work.
# The daemon runs each in a pooled worktree as it has a slot and a tree, so
# this cast takes no branch and asks for no share. Queued rather than
# awaited: each branch's row is its own cast's to say. Every component is
# passed on as this cast took it, so the children work the way the parent
# was asked to; `--unattended` reaches them through vekna.
@step
async def summon(run: Summon) -> Tally | Summon:
    if not run.queue:
        return run.to(Tally)
    pull = run.queue[0]
    row = await _surveyed(run.project, pull)
    emit_delta(services().report.surveyed(row))
    after = run.took(row)
    if isinstance(row, Unsurveyed) or not after.worked(row.todos):
        return after.to(Summon)
    asked = HealPr(
        number=pull.number, bound=run.bound, attended=run.attended, batch=run.batch
    )
    try:
        cast = await enqueue("heal.pr", asked)
    except NoDaemonError:
        stopped = (
            "heal.mine queues a cast per pull request and needs the daemon:"
            " start it with `vekna`"
        )
        return after.but(stopped=stopped).to(Tally)
    queued = Queued(number=pull.number, branch=pull.branch, cast=cast)
    return after.summoned(queued).to(Summon)


# One pull request the forge or git would not answer about is a row saying
# so, not the end of the cast: the next one may answer fine.
async def _surveyed(project: Project, pull: PullRequest) -> Surveyed | Unsurveyed:
    forge = services().forge(project)
    try:
        board = await forge.board(pull.branch)
        threads = await forge.threads(pull.number)
        if (conflicted := pull.conflicted) is None:
            conflicted = await services().scm(project).conflicts(pull.base, pull.branch)
    except (ForgeError, ScmError) as error:
        return Unsurveyed(
            number=pull.number, branch=pull.branch, url=pull.url, note=str(error)
        )
    facts = Facts(pull=pull, board=board, threads=threads, conflicted=conflicted)
    return services().todos.surveyed(facts, project)


# Nothing to await: this routes and renders. The summary is said before the
# failure is raised, which is the whole reason every ending routes here rather
# than raising where it happened. A plan has nothing to add to the lines the
# survey already said.
@step
def chart(run: Chart) -> Done[Healed]:
    if run.stopped or run.tasks:
        emit_delta(services().report.healed(run))
    if run.stopped:
        raise RitualError(run.stopped)
    return Done(
        Healed(
            surveyed=run.surveyed,
            checked=run.checked,
            not_reached=[pull.branch for pull in run.queue],
        )
    )


# `chart` for `heal.mine`: the casts it queued rather than branches it worked.
@step
def tally(run: Tally) -> Done[Healed]:
    if run.stopped or run.tasks:
        emit_delta(services().report.queued(run))
    if run.stopped:
        raise RitualError(run.stopped)
    return Done(
        Healed(
            surveyed=run.surveyed,
            not_reached=[pull.branch for pull in run.queue],
            queued=run.queued,
        )
    )


# --- taking a branch -------------------------------------------------------


@step
async def check_clean(work: CheckClean) -> Chart | SyncBranch:
    try:
        dirty = await services().scm(work.run.project).status()
    except ScmError as error:
        return work.abandoned(str(error)).to(Chart)
    if dirty:
        # Fatal by design: everything below this line moves branches around,
        # and doing that over someone's uncommitted work is how it gets lost.
        return work.abandoned(f"the worktree is not clean:\n{dirty}").to(Chart)
    return work.to(SyncBranch)


# Fetch, then stand on the branch as the remote has it.
@step
async def sync_branch(work: SyncBranch) -> Chart | SkipPr | SetAside | Tend:
    scm = services().scm(work.run.project)
    pull = work.pr
    try:
        await scm.fetch()
    except ScmError as error:
        return work.abandoned(str(error)).to(Chart)
    # On its own rather than chained to the rest, because the failures are
    # different answers: a checkout that will not go through is another
    # worktree standing on the branch, and that is nobody's fault.
    try:
        await scm.checkout(pull.branch)
    except ScmError as error:
        return work.but(note=str(error)).to(SkipPr)
    try:
        await scm.catch_up(pull.branch)
    except ScmError as error:
        return work.but(note=str(error)).to(SetAside)
    return work.to(Tend)


# Each task's first step, the one `tend` hands a branch.
_First: TypeAlias = MergeBase | RerunJobs | SettleLeft | QualityReview | PostGuide

# Keyed by every `Task`, so a task added without a step here fails the test
# that walks each one through `tend`.
_FIRST: dict[Task, type[_First]] = {
    "merge": MergeBase,
    "ci": RerunJobs,
    "answer": SettleLeft,
    "review": QualityReview,
    "guide": PostGuide,
}


# Hand the branch its next task, or let it go. Whatever this cast committed is
# pushed first: every task after the merge works on code the forge has, and a
# branch is not left with commits only this worktree holds.
@step
def tend(work: Tend) -> PushWork | FinishPr | _First:
    if work.changed:
        return work.to(PushWork)
    if not work.todos:
        return work.to(FinishPr)
    task, *rest = work.todos
    taken = work.but(todos=rest)
    return taken.to(_FIRST[task])


# --- merge -----------------------------------------------------------------


# Merge the base in. Only a conflict brings a branch here, so a merge that
# goes through is the forge's answer gone stale, and still owes the gate.
@step
async def merge_base(work: MergeBase) -> Tend | GateCheck | ResolveConflicts:
    scm = services().scm(work.run.project)
    base = work.base_ref
    # Asked before the merge rather than read off it afterwards: git says
    # "Already up to date" in whatever language the terminal is set to.
    if await scm.contains(base):
        return work.but(note=f"{base} is already merged in").to(Tend)
    merged = await scm.merge(base)
    if merged.exit_code == 0:
        return work.to(GateCheck)
    # The index is read once, by the step below. What this carries there is
    # why the merge failed, for the one case that is not a conflict at all.
    said = services().verdicts.said(merged)
    return work.merging_on(f"git merge failed: {said}").to(ResolveConflicts)


# Hand the conflicted files to an agent until the index comes back clean.
@step
async def resolve_conflicts(
    work: ResolveConflicts,
) -> SetAside | GateCheck | StandDown | Chart | ResolveConflicts:
    project = work.run.project
    try:
        unmerged = await services().scm(project).unmerged()
    except ScmError as error:
        return work.but(note=str(error)).to(SetAside)
    if not unmerged:
        # Nothing conflicted and nothing tried yet: the merge failed for a
        # reason no agent can fix, and the note says which.
        if not work.spent(resolve_conflicts.name):
            return work.but(note=f"no conflicts: {work.note}").to(SetAside)
        return work.but(note="").cleared(resolve_conflicts.name).to(GateCheck)
    # The budget's say or the operator's: the branch stands down either way.
    if work.exhausted(resolve_conflicts.name) or not await _worth_another(
        work, "resolve the conflicts"
    ):
        stopped = work.stopped_by("the merge conflicts were not resolved")
        return stopped.to(StandDown)
    prompt = services().prompts.resolve(
        project, base=work.base_ref, branch=work.pr.branch, files="\n".join(unmerged)
    )
    fallen = (
        await services()
        .agent(project)
        .ask(
            prompt,
            role="writer",
            key=_session(work, "merge"),
            attended=work.run.attended,
        )
    )
    if fallen:
        return work.abandoned(fallen.reason).to(Chart)
    # Back through this same step, which re-reads git rather than believing
    # the agent. The note goes now: past here the merge failing is just what a
    # conflict looks like, and the row is not to be told about it twice.
    return work.but(note="").charged(resolve_conflicts.name)


# A branch this cast has stopped paying for, carrying whatever the round
# learned into the cast's memory: the next branch broken the same way stands
# down without spending a budget of its own.
def _gave_up(work: Work, reason: str, seen: list[str]) -> Work:
    return work.stopped_by(reason).but(run=work.run.but(seen=seen))


# Spending the agent's time is the operator's call where there is one: an
# attended cast asks before every repair attempt, an unattended one lets the
# budget answer, since with nobody there a prompt is a hang.
async def _worth_another(work: Work, what: str) -> bool:
    if not work.run.attended:
        return True
    return await decide(f"{what} on {work.pr.branch} (attempt {work.attempts() + 1})?")


# One round of a repair loop, shared by every loop that runs a gate, against
# the commands `against` names as a CI job would. The branch comes back
# charged and pointed at what to run next, or green and sent on to `then`, or
# given up on. `work.gate` is the task that broke last time round, where the
# runner named one: an agent working on one linter is judged by that linter,
# not by the whole chain in front of it.
async def _repaired(
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
    # The budget had its say; the operator gets the last one, and a verdict
    # nobody will pay for again is remembered either way.
    if not await _worth_another(work, f"repair `{gate}`"):
        return _gave_up(work, ruling.declined, ruling.seen).to(StandDown)
    if fallen := await _asked(work, ruling.asking, key=name):
        return work.abandoned(fallen.reason).to(Chart)
    return work.but(gate=ruling.next_gate).charged(name)


# The agent session `name` names on this branch. Built here and nowhere else:
# a step that opens a session and the loop that continues it must agree.
def _session(work: Work, name: str) -> str:
    return f"{name}-{work.pr.number}"


# A writer, in the session `key` names on this branch: every round of a loop
# continues the one before it.
async def _asked(work: Work, prompt: str, *, key: str) -> Fallen | None:
    return (
        await services()
        .agent(work.run.project)
        .ask(prompt, role="writer", key=_session(work, key), attended=work.run.attended)
    )


# Run the gate, and repair it until it is green or the budget is gone.
@step
async def gate_check(work: GateCheck) -> GateCheck | FinishMerge | StandDown | Chart:
    against = CiJob(gate=work.run.project.gate)
    return await _repaired(work, against, name=gate_check.name, then=FinishMerge)


# Close an open merge and commit whatever the repairs left behind.
@step
async def finish_merge(work: FinishMerge) -> SetAside | Tend:
    scm = services().scm(work.run.project)
    if work.merging:
        try:
            await scm.continue_merge()
        except ScmError as error:
            return work.but(note=str(error)).to(SetAside)
    # A clean merge leaves the gate repairs uncommitted, and a merge the agent
    # committed itself leaves them behind too. Either way this is where they
    # land — and it is a no-op when there is nothing to land.
    try:
        await scm.commit(f"chore: merge {work.pr.base} and fix the gates")
    except ScmError as error:
        return work.but(note=f"could not commit the merge: {error}").to(SetAside)
    return work.merged().to(Tend)


# What comes back is this act's own bookkeeping and nothing else — the callers
# join it to whatever else the row is carrying.
async def _released(work: Work) -> str:
    try:
        stashed = await services().scm(work.run.project).release(work.pr.branch)
    except ScmError as error:
        return str(error)
    return f'stashed as "{stashed}"' if stashed else ""


# A branch whose gate will not go green still has its other tasks, so it goes
# back to `tend` rather than out. The worktree goes back first: half a repair
# is not something to review.
@step
async def stand_down(work: StandDown) -> Tend:
    return work.standing_down(await _released(work)).to(Tend)


# --- push ------------------------------------------------------------------


# Not fatal, and not `set_aside`: a push that will not go through costs the
# review its anchors and nothing else. What is left behind is said twice over:
# in this note, and in the row's `unpushed`, counted off git at the end.
@step
async def push_work(work: PushWork) -> Tend:
    try:
        await services().scm(work.run.project).push(work.pr.branch)
    except ScmError as error:
        work = work.noting(str(error))
    return work.pushed().to(Tend)


# --- ci --------------------------------------------------------------------


# The job the check in hand belongs to. Every red check has one: the survey
# reads only the checks a job is configured for.
def _job(work: Work) -> CiJob:
    return work.run.project.ci.job(work.red[0].name) or CiJob()


# A job loop's name for the check in hand: the budget it spends, and the
# session every round continues, from the mend that read the log through the
# gate. The next job starts on a session of its own.
def _loop(work: Work, name: str) -> str:
    return f"{name}-{work.red[0].name}"


# Rerun first, wherever the job asks for it. Whatever went again is CI's to
# answer, so the task ends there: a fix pushed on top would start a run of its
# own and waste the rerun. The next cast reads the result. A rerun is a
# flake's second chance, not a loop: a check this head has already run more
# than once is fixed instead.
@step
async def rerun_jobs(work: RerunJobs) -> Tend | PickJob:
    project = work.run.project
    forge = services().forge(project)
    went: list[str] = []
    notes: list[str] = []
    for check in work.red:
        job = project.ci.job(check.name)
        if job is None or not job.rerun:
            continue
        try:
            if await forge.runs(work.pr.branch, check) > 1:
                continue
            await forge.rerun(check)
            went.append(check.name)
        except ForgeError as error:
            notes.append(str(error))
    if went:
        notes.append(f"reran {', '.join(went)}")
        return work.noting(*notes).to(Tend)
    return work.noting(*notes).one_per_job().to(PickJob)


# The next red check, handed to the loop that fixes its kind of job.
@step
def pick_job(work: PickJob) -> Tend | CloseGap | MendJob:
    if not work.red:
        return work.to(Tend)
    if _job(work).covering:
        return work.to(CloseGap)
    return work.to(MendJob)


# The agent reads how the job failed on CI and fixes it. A job with a gate
# then goes round the repair loop against it, in the same session; one without
# is committed as the agent left it, and the push is what checks it.
@step
async def mend_job(work: MendJob) -> PickJob | JobGate | LandJob | Chart:
    project = work.run.project
    check = work.red[0]
    gate = _job(work).gate
    try:
        log = await services().forge(project).log(check)
    except ForgeError as error:
        # The gate can still find what the log would have said.
        if gate:
            return work.noting(str(error)).to(JobGate)
        return work.passed_over(str(error)).to(PickJob)
    if not await _worth_another(work, f"fix the `{check.name}` job"):
        return work.passed_over(f"`{check.name}` was left red, as you decided").to(
            PickJob
        )
    prompt = services().prompts.fix_job(
        project, services().verdicts.logged(log), job=check.name, gate=gate
    )
    if fallen := await _asked(work, prompt, key=_loop(work, job_gate.name)):
        return work.abandoned(fallen.reason).to(Chart)
    return work.to(JobGate) if gate else work.to(LandJob)


# A job's repair loop. Standing down ends the ci task, so the checks still
# behind the one in hand are named rather than carried off unread.
async def _mended(
    work: _WorkT, against: CiJob, *, name: str
) -> LandJob | _WorkT | StandDown | Chart:
    went = await _repaired(work, against, name=name, then=LandJob)
    return went.leaving_red() if isinstance(went, StandDown) else went


# The job's gate, repaired until it is green: the merge's loop, run against
# the job's own commands.
@step
async def job_gate(work: JobGate) -> JobGate | LandJob | StandDown | Chart:
    return await _mended(work, _job(work), name=_loop(work, job_gate.name))


# Close the coverage gap, repairing a red suite like any other gate. The first
# measurement is the whole one, because it decides whether there is a gap at
# all; a repair round re-runs the fast one, or the single task that broke.
@step
async def close_gap(work: CloseGap) -> CloseGap | LandJob | StandDown | Chart:
    project = work.run.project
    job = _job(work)
    against = CiJob(
        gate=job.gate or project.coverage,
        fast=job.fast or project.fast_coverage,
        covering=True,
    )
    # Anything but the full measurement is a reason to spend the full
    # measurement, not a branch that is covered.
    return await _mended(work, against, name=_loop(work, close_gap.name))


# Each job's fix is a commit of its own. A fix that changed nothing is no
# commit at all, and no fix either: green here and red on CI, the job is left
# red and the row says so.
@step
async def land_job(work: LandJob) -> PickJob | SetAside:
    name = work.red[0].name
    message = (
        "test: cover the lines this branch changes"
        if _job(work).covering
        else f"fix: make the {name} job green"
    )
    try:
        committed = await services().scm(work.run.project).commit(message)
    except ScmError as error:
        return work.noting(f"could not commit the {name} fix: {error}").to(SetAside)
    if not committed:
        return work.passed_over(f"`{name}` passes here; CI is still red").to(PickJob)
    return work.landed().to(PickJob)


# --- answer ----------------------------------------------------------------


async def _unsettled(project: Project, number: int) -> list[Thread]:
    threads = await services().forge(project).threads(number)
    return [thread for thread in threads if not thread.resolved]


# The ritual's reply under a thread, then the thread settled: in that order,
# so a forge that fails between them leaves the mark `settle_left` reads.
async def _settled(
    forge: ForgeProtocol, number: int, thread: Thread, reply: str
) -> None:
    await forge.reply(number, thread, signed(reply))
    await forge.resolve(number, thread)


def _filed(url: str) -> str:
    return f"Filed as {url}"


# Settle what an earlier round left half done, and say how many threads that
# was.
async def _finished(
    forge: ForgeProtocol, number: int, threads: list[Thread], listing: Listing
) -> int:
    answered = [thread for thread in threads if thread.answered]
    unanswered = [thread for thread in threads if not thread.answered]
    filed = [
        (thread, issue)
        for thread in unanswered
        if (issue := filed_as(listing.issues, thread.id)) is not None
    ]
    for thread in answered:
        await forge.resolve(number, thread)
    for thread, issue in filed:
        await _settled(forge, number, thread, _filed(issue.url))
    return len(answered) + len(filed)


# Finish a round an earlier cast's forge failure cut short, before anything is
# read: a thread whose last word is the ritual's reply only wants settling,
# and one an open issue was filed for wants the reply naming it. A backlog the
# forge would not list whole may hide the issue filed for a thread, and
# reading that thread again would file it twice, so the task ends there. A
# branch still wearing the answered label from an earlier cast has threads
# open again, so the label comes off first.
@step
async def settle_left(work: SettleLeft) -> ReadThreads | Tend:
    project = work.run.project
    forge = services().forge(project)
    answered = project.labels.answered
    try:
        if work.pr.wears(answered):
            await forge.label(work.pr.number, remove=[answered])
        threads = await _unsettled(project, work.pr.number)
        # Only a thread with no reply yet can have an issue filed for it.
        unanswered = any(not thread.answered for thread in threads)
        listing = (
            services().backlog.merged(await forge.issues()) if unanswered else Listing()
        )
    except ForgeError as error:
        return work.noting(str(error)).to(Tend)
    if listing.truncated:
        note = (
            "the forge would not list every open issue, so an issue filed for"
            " an open thread may be missing from it"
        )
        return work.noting(note).to(Tend)
    try:
        done = await _finished(forge, work.pr.number, threads, listing)
    except ForgeError as error:
        return work.noting(str(error)).to(Tend)
    if done:
        emit_delta(f"{work.pr.branch}: settled {done} threads an earlier cast left")
    return work.to(ReadThreads)


# Where a round finds nothing more to do. A branch the writer has worked on
# goes to the gate with whatever it changed, and a branch it never touched, or
# touched without changing a file, has nothing to land.
async def _landing(work: Work, note: str = "") -> Tend | AnswerGate | SetAside:
    work = work.noting(note)
    if not work.spent(answer_threads.name):
        return work.to(Tend)
    try:
        dirty = await services().scm(work.run.project).status()
    except ScmError as error:
        return work.noting(str(error)).to(SetAside)
    return work.to(AnswerGate) if dirty else work.to(Tend)


# The next batch of open threads, saying how many it leaves for later; none
# once the rounds are spent, without asking the forge. A forge with none open
# is the task done, and the branch wears the answered label for it.
async def _batch(work: Work) -> list[Thread]:
    if work.spent(read_threads.name) >= ROUNDS:
        return []
    project = work.run.project
    if not (threads := await _unsettled(project, work.pr.number)):
        await services().forge(project).label(
            work.pr.number, add=[project.labels.answered]
        )
    batch = threads[: work.run.batch]
    if len(batch) < len(threads):
        emit_delta(
            f"{work.pr.branch}: {len(threads)} threads open,"
            f" reading {len(batch)} of them"
        )
    return batch


# Read the next batch of open threads into a triage. Read again after every
# round: an item is triaged against the code as it stands, and a thread the
# last round settled is no longer open.
@step
async def read_threads(
    work: ReadThreads,
) -> AskTriage | Tend | AnswerGate | SetAside | Chart:
    try:
        batch = await _batch(work)
    except ForgeError as error:
        return await _landing(work, str(error))
    if not batch:
        return await _landing(work)
    read = (
        await services()
        .agent(work.run.project)
        .ask_for(
            services().prompts.triage_read(work.pr.number, batch),
            output=TriageNotes,
            role="reader",
            attended=work.run.attended,
        )
    )
    if isinstance(read, Fallen):
        return work.abandoned(read.reason).to(Chart)
    if isinstance(read, Misread):
        return await _landing(work, read.reason)
    # The forge said a thread was open, so an empty reading is the reading
    # disagreeing with the forge rather than a branch with nothing to do.
    if not read.items:
        return await _landing(
            work, "the reading found nothing, but the forge says otherwise"
        )
    return AskTriage(
        work=work.charged(read_threads.name), items=read.items, threads=batch
    )


# Put the triage on your terminal and take your answer to each item.
@step
async def ask_triage(triage: AskTriage) -> AnswerThreads:
    report = services().report
    emit_delta("\n".join(report.triage(triage.items)))
    told: list[str] = []
    for index, item in enumerate(triage.items, start=1):
        # Free text and not a choice: an item is answered by saying how the
        # thing is supposed to work, which no four options carry. An empty
        # answer agrees with the reading's own proposal.
        said = await decide(f"{report.shown(index, item)}\n->", free=True)
        told.append(said or f"{item.action} it, as the reading says")
    work = triage.work
    prompt = services().prompts.triage_work(work.pr.number, triage.items, told)
    triaged = {item.thread for item in triage.items}
    threads = [thread for thread in triage.threads if thread.id in triaged]
    return AnswerThreads(work=work, prompt=prompt, threads=threads)


# The agent edits code and drafts every reply; it reaches the forge for
# nothing, so what it hands back is posted by the step after this one. Straight
# in, with nothing asked: the triage was answered item by item a step ago. The
# gate's repairs continue the same session, so they meet an agent that
# remembers what it changed and why.
@step
async def answer_threads(
    instructed: AnswerThreads,
) -> PostAnswers | Tend | AnswerGate | SetAside | Chart:
    work = instructed.work.charged(answer_threads.name)
    came = (
        await services()
        .agent(work.run.project)
        .ask_for(
            instructed.prompt,
            output=Answered,
            role="writer",
            key=_session(work, answer_gate.name),
            attended=work.run.attended,
        )
    )
    if isinstance(came, Fallen):
        return work.abandoned(came.reason).to(Chart)
    if isinstance(came, Misread):
        return await _landing(work, came.reason)
    return PostAnswers(work=work, items=came.items, threads=instructed.threads)


# An issue is opened before the reply that names it, and a thread is settled
# after the reply that answers it; both carry a mark `settle_left` reads back
# when the forge fails between them. A thread the agent invented is said and
# skipped; a thread it left unanswered stays open, and the next round reads it
# again. Answers with how many threads were settled.
async def _posted(answering: PostAnswers) -> int:
    work = answering.work
    number = work.pr.number
    forge = services().forge(work.run.project)
    threads = {thread.id: thread for thread in answering.threads}
    settled = 0
    for item in answering.items:
        if item.thread not in threads:
            emit_delta(f"the agent answered a thread nobody triaged: {item.thread}")
            continue
        reply = item.reply
        if item.issue is not None:
            body = f"{item.issue.body}\n\n{filed_for(item.thread)}"
            opened = await forge.issue(item.issue.title, body)
            reply = f"{reply}\n\n{_filed(opened.url)}"
        await _settled(forge, number, threads[item.thread], reply)
        settled += 1
    return settled


# The forge writes, in a step of their own, apart from the agent's. Round
# again rather than straight to the gate: what the forge still holds open is
# the next batch, and `read_threads` is what finds out there is none. A round
# that settled nothing would read the same batch back, so it lands with
# whatever the agent did change, and so does a forge that refused partway:
# the fixes are real whether or not every reply went up.
@step
async def post_answers(
    answering: PostAnswers,
) -> ReadThreads | Tend | AnswerGate | SetAside:
    work = answering.work
    try:
        settled = await _posted(answering)
    except ForgeError as error:
        return await _landing(work, str(error))
    if not settled:
        return await _landing(work)
    return work.to(ReadThreads)


# The gate over what the answers changed, repaired until it is green: the
# merge's loop, in the session the answers were written in.
@step
async def answer_gate(work: AnswerGate) -> AnswerGate | LandAnswers | StandDown | Chart:
    against = CiJob(gate=work.run.project.gate)
    return await _repaired(work, against, name=answer_gate.name, then=LandAnswers)


@step
async def land_answers(work: LandAnswers) -> Tend | SetAside:
    try:
        await services().scm(work.run.project).commit("chore: act on the review triage")
    except ScmError as error:
        return work.noting(f"could not commit the answers: {error}").to(SetAside)
    return work.committed().to(Tend)


# --- review ----------------------------------------------------------------


# Post the review and label the branch: the one task with no budget and no
# loop, because there is nothing here to retry against. An agent that found
# nothing to post is indistinguishable from one that read badly, so the label
# goes on either way, and a review that came out empty is yours to notice and
# ask for again by taking it off. What the branch already said stays in the
# note: a stash or a failed push is still news when the review fails too.
@step
async def quality_review(work: QualityReview) -> Tend | SetAside | Chart:
    project = work.run.project
    number = work.pr.number
    try:
        threads = await services().forge(project).threads(number)
    except ForgeError as error:
        return work.noting(str(error)).to(SetAside)
    prompt = services().prompts.review(
        project, base=work.base_ref, threads=threads, reason=work.reason
    )
    read = (
        await services()
        .agent(project)
        .ask_for(
            prompt,
            output=Findings,
            role="reader",
            key=_session(work, "review"),
            attended=work.run.attended,
        )
    )
    if isinstance(read, Fallen):
        return work.abandoned(read.reason).to(Chart)
    if isinstance(read, Misread):
        return work.noting(read.reason).to(SetAside)
    findings = services().report.findings(project, read.items)
    if note := await _put_up(project, number, findings):
        return work.noting(note).to(SetAside)
    return work.to(Tend)


# Put every item up, label the branch, and say what did not happen. A posting
# that got partway still earns the label: what is up cannot be taken down, and
# an unlabelled branch is one the next cast reviews again, saying all of it a
# second time. Only a posting that got nowhere is left unlabelled — an empty
# review is labelled, for the reason above `quality_review`.
async def _put_up(project: Project, number: int, findings: list[Finding]) -> str:
    forge = services().forge(project)
    posted = await forge.comment(number, findings)
    if posted.count or not posted.stopped:
        try:
            await forge.label(number, add=[project.labels.reviewed])
        except ForgeError as error:
            return str(error)
    if not posted.stopped:
        return ""
    return f"{posted.count} of {len(findings)} review items went up: {posted.stopped}"


# --- guide -----------------------------------------------------------------


# Post the smoke-test guide and label the branch: like the review, no budget
# and no loop. The comment goes up before the label, so a label the forge
# refuses leaves a guide the next cast edits rather than posts again.
@step
async def post_guide(work: PostGuide) -> Tend | SetAside | Chart:
    project = work.run.project
    number = work.pr.number
    read = (
        await services()
        .agent(project)
        .ask_for(
            services().prompts.guide(project, base=work.base_ref),
            output=Guide,
            role="reader",
            key=_session(work, "guide"),
            attended=work.run.attended,
        )
    )
    if isinstance(read, Fallen):
        return work.abandoned(read.reason).to(Chart)
    if isinstance(read, Misread):
        return work.noting(read.reason).to(SetAside)
    forge = services().forge(project)
    try:
        await forge.note(number, read.body, marker=GUIDE_MARK)
        await forge.label(number, add=[project.labels.qa])
    except ForgeError as error:
        return work.noting(str(error)).to(SetAside)
    return work.to(Tend)


# --- endings ---------------------------------------------------------------


# Write the branch's row into the cast, and go on to the next one.
@step
async def finish_pr(work: FinishPr) -> Survey:
    row = work.checked(
        "blocked" if work.blocked else "worked",
        # Asked of git rather than tracked in the payload: what needs pushing
        # is what the remote has not got, whoever put it there.
        unpushed=await services().scm(work.run.project).ahead(work.pr.branch),
        note=work.telling(),
    )
    return work.run.rowed(row).to(Survey)


# Leave the branch where it is, and say so in the report. Nothing to release
# and nothing to count: this is only reached where the checkout itself would
# not go through, so the worktree never moved and the branch is exactly as its
# owner left it.
@step
def skip_pr(work: SkipPr) -> Survey:
    row = work.checked("skipped", unpushed=None, note=work.telling())
    return work.run.rowed(row).to(Survey)


# Give the worktree back and report the branch blocked.
@step
async def set_aside(work: SetAside) -> Survey:
    # The worktree goes back before the count, not as an argument alongside
    # it: what is left to push is asked of a tree this step has finished with.
    released = await _released(work)
    row = work.checked(
        "blocked",
        unpushed=await services().scm(work.run.project).ahead(work.pr.branch),
        # A branch that stood down and then failed the review arrives here
        # with two things to say, and the second must not cost it the first:
        # the report needs to tell the red gate.
        note=work.telling(released),
    )
    return work.run.rowed(row).to(Survey)
