"""Heal your pull requests: each one taken as far as its tasks go.

    vekna cast heal.mine [--plan-only true] [--bound N] [--attended true]
    vekna cast heal.this [--plan-only true] [--bound N] [--attended true]
    vekna cast merge [--plan-only true] [--bound N] [--attended true]
    vekna cast ci [--plan-only true] [--bound N] [--attended true]
    vekna cast review [--plan-only true] [--attended true]

``heal.mine`` takes every open pull request of yours not wearing the wait
label, oldest-modified first; ``heal.this`` and the task rituals take the pull
request of the branch at the cwd. A task ritual is ``heal.this`` that may work
one task and no other.

Each pull request is surveyed first: whether it conflicts with its base, which
of the configured CI jobs are red, how many review threads are open, and which
labels it wears. That becomes its todo list, in the order a cast works it:
merge, ci, answer, review, guide. Facts make a todo; the reviewed and qa labels
only take one away. The list is printed a line per pull request as it is read.
With ``--plan-only true`` that is all: no checkout, no commit, no label.

Otherwise a branch with a task this cast works is taken: the worktree must be
clean, the base is brought up to date, and the branch is checked out and
fast-forwarded to the remote. Then ``tend`` hands it each task in turn, and
every task ends back at ``tend``:

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
- **review**: the quality review, as inline comments, then the reviewed label.
  Whatever this cast committed is pushed first, so the comments anchor to code
  the forge has.

What a cast committed and has not pushed goes up before the branch is left.
Nothing waits for CI after a push, and nothing merges a branch that is merely
behind.

Neither the gate nor the coverage is re-run whole while a repair is underway.
Where the runner names the task that broke, the next round runs that task
alone, and the gate itself runs once more when it comes back green.

A branch is left alone rather than reported broken when the checkout will not
go through, which is what another worktree standing on it looks like. Checking
out the base branch is not the same thing, so that one ends the cast.

Two things end the whole cast rather than one branch: a worktree that is not
clean, and an agent that dies mid-flight. Both still print the report first,
then fail the cast.

Budgets are per step and per branch: a step may be retried ``--bound`` times,
going green clears its count, and moving to the next pull request clears them
all. A verdict a step already gave up on once is not paid for twice: the next
branch whose gate says the same thing stands down without spending its budget.
Unattended, nothing is asked and the budgets decide; attended, each repair
attempt is put to you first.

A branch is taken only where the worst it can spend still fits the engine's
step budget; one that does not ends the cast without failing it, and the report
names what was not reached.
"""

from typing import TypeVar

from vekna.folio.flow import decide
from vekna.lexicon import Done, RitualError, emit_delta, step

from cabinet.pacts.agent import Fallen, Misread
from cabinet.pacts.forge import ForgeError
from cabinet.pacts.heal import (
    Chart,
    CheckClean,
    CloseGap,
    FinishMerge,
    FinishPr,
    GateCheck,
    JobGate,
    LandJob,
    MendJob,
    MergeBase,
    MusterMine,
    MusterThis,
    PickJob,
    PushWork,
    QualityReview,
    RerunJobs,
    ResolveConflicts,
    SetAside,
    SkipPr,
    StandDown,
    Survey,
    SyncBranch,
    Tend,
)
from cabinet.pacts.healing import (
    Facts,
    Healed,
    Run,
    Surveyed,
    Task,
    Unsurveyed,
    Work,
    joined,
)
from cabinet.pacts.project import CiJob, Project
from cabinet.pacts.pulls import PullRequest
from cabinet.pacts.repairs import Attempt, Fixed, Stalled
from cabinet.pacts.scm import ScmError
from cabinet.pacts.services import services
from cabinet.pacts.threads import Finding, Findings

_WorkT = TypeVar("_WorkT", bound=Work)
_ThenT = TypeVar("_ThenT", bound=Work)

# --- the cast --------------------------------------------------------------


# Before the first fetch: an ssh remote would ask for a passphrase on a
# terminal no command under a cast has, and the answer is a config line.
async def _listed(run: Run) -> list[PullRequest]:
    await services().scm(run.project).preflight()
    return await services().forge(run.project).pulls()


# Queued, with every step that works no branch spoken for now that the queue
# is known.
def _queued(run: Run, queue: list[PullRequest]) -> Survey:
    opening = services().steps.opening(len(queue))
    return run.but(queue=queue).spoke_for(opening).to(Survey)


# Every open pull request of yours the forge lists, bar the parked ones.
@step
async def muster_mine(run: MusterMine) -> Chart | Survey:
    try:
        pulls = await _listed(run)
    except (ScmError, ForgeError) as error:
        return run.but(stopped=str(error)).to(Chart)
    return _queued(run, services().pulls.wanted(pulls, run.project))


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
    return _queued(run, queue)


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


# Update the base branch, then stand on the branch as the remote has it.
@step
async def sync_branch(work: SyncBranch) -> Chart | SkipPr | SetAside | Tend:
    scm = services().scm(work.run.project)
    pull = work.pr
    try:
        await scm.sync_base(pull.base)
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


# Each task's first step. Keyed by every `Task`, so a task added without a
# step here fails the test that walks each one through `tend`.
_FIRST: dict[Task, type[MergeBase | RerunJobs | QualityReview]] = {
    "merge": MergeBase,
    "ci": RerunJobs,
    "review": QualityReview,
}


# Hand the branch its next task, or let it go. Whatever this cast committed is
# pushed first: every task after the merge works on code the forge has, and a
# branch is not left with commits only this worktree holds.
@step
def tend(work: Tend) -> PushWork | FinishPr | MergeBase | RerunJobs | QualityReview:
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
    # Asked before the merge rather than read off it afterwards: git says
    # "Already up to date" in whatever language the terminal is set to.
    if await scm.contains(work.pr.base):
        return work.but(note=f"{work.pr.base} is already merged in").to(Tend)
    merged = await scm.merge(work.pr.base)
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
        project, base=work.pr.base, branch=work.pr.branch, files="\n".join(unmerged)
    )
    fallen = (
        await services()
        .agent(project)
        .ask(
            prompt,
            role="writer",
            key=f"merge-{work.pr.number}",
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


# One round of a repair loop, shared by every loop that runs a gate. The
# branch comes back charged and pointed at what to run next, or green and
# handed to `then`, or given up on. `work.gate` is the task that broke last
# time round, where the runner named one: an agent working on one linter is
# judged by that linter, not by the whole chain in front of it.
async def _repaired(
    work: _WorkT, then: type[_ThenT], *, name: str, whole: str, fast: str = ""
) -> _ThenT | _WorkT | StandDown | Chart:
    project = work.run.project
    gate = work.gate or whole
    ran = await services().tasks(project).run(gate)
    ruling = services().repairs.ruling(
        Attempt(
            project=project,
            ran=ran,
            gate=gate,
            whole=whole,
            fast=fast,
            spent=work.spent(name),
            bound=work.run.bound,
            seen=work.run.seen,
            # The coverage loop is the one whose step closes a gap.
            covering=isinstance(work, CloseGap),
        )
    )
    if isinstance(ruling, Fixed):
        # A task passing on its own is not the gate passing — it is the reason
        # to spend the gate. The whole chain runs once more.
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


# A writer, in the session `key` names on this branch: every round of a loop
# continues the one before it.
async def _asked(work: Work, prompt: str, *, key: str) -> Fallen | None:
    return (
        await services()
        .agent(work.run.project)
        .ask(
            prompt,
            role="writer",
            key=f"{key}-{work.pr.number}",
            attended=work.run.attended,
        )
    )


# Run the gate, and repair it until it is green or the budget is gone.
@step
async def gate_check(work: GateCheck) -> GateCheck | FinishMerge | StandDown | Chart:
    return await _repaired(
        work, FinishMerge, name=gate_check.name, whole=work.run.project.gate
    )


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
        work = work.but(note=joined(work.note, str(error)))
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
        return work.but(note=joined(work.note, *notes)).to(Tend)
    return work.but(note=joined(work.note, *notes)).one_per_job().to(PickJob)


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
            return work.but(note=joined(work.note, str(error))).to(JobGate)
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
    work: _WorkT, *, name: str, whole: str, fast: str
) -> LandJob | _WorkT | StandDown | Chart:
    went = await _repaired(work, LandJob, name=name, whole=whole, fast=fast)
    return went.leaving_red() if isinstance(went, StandDown) else went


# The job's gate, repaired until it is green: the merge's loop, run against
# the job's own commands.
@step
async def job_gate(work: JobGate) -> JobGate | LandJob | StandDown | Chart:
    job = _job(work)
    return await _mended(
        work, name=_loop(work, job_gate.name), whole=job.gate, fast=job.fast
    )


# Close the coverage gap, repairing a red suite like any other gate. The first
# measurement is the whole one, because it decides whether there is a gap at
# all; a repair round re-runs the fast one, or the single task that broke.
@step
async def close_gap(work: CloseGap) -> CloseGap | LandJob | StandDown | Chart:
    project = work.run.project
    job = _job(work)
    return await _mended(
        work,
        name=_loop(work, close_gap.name),
        whole=job.gate or project.coverage,
        fast=job.fast or project.fast_coverage,
    )


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
        note = joined(work.note, f"could not commit the {name} fix: {error}")
        return work.but(note=note).to(SetAside)
    if not committed:
        return work.passed_over(f"`{name}` passes here; CI is still red").to(PickJob)
    return work.landed().to(PickJob)


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
        return work.but(note=joined(work.note, str(error))).to(SetAside)
    prompt = services().prompts.review(
        project, base=work.pr.base, threads=threads, reason=work.reason
    )
    read = (
        await services()
        .agent(project)
        .ask_for(
            prompt,
            output=Findings,
            role="reader",
            key=f"review-{number}",
            attended=work.run.attended,
        )
    )
    if isinstance(read, Fallen):
        return work.abandoned(read.reason).to(Chart)
    if isinstance(read, Misread):
        return work.but(note=joined(work.note, read.reason)).to(SetAside)
    findings = services().report.findings(project, read.items)
    if note := await _put_up(project, number, findings):
        return work.but(note=joined(work.note, note)).to(SetAside)
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
