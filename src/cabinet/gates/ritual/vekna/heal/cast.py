"""The cast: mustering the pull requests, surveying each, and the report."""

from typing import TypeVar

from vekna.folio.flow import enqueue

# The wait `await_cast` makes after its own enqueue, taken alone: `summon`
# has queued the casts by then, and vekna exports no other way to wait on one.
from vekna.folio.flow._mills import awaited
from vekna.lexicon import (
    CastFailedError,
    Done,
    NoDaemonError,
    RitualError,
    attended,
    emit_delta,
    step,
)

from cabinet.gates.ritual.vekna.heal.branch import uncommitted
from cabinet.pacts.forge import ForgeError
from cabinet.pacts.heal import (
    Attend,
    Chart,
    CheckClean,
    MusterMain,
    MusterMine,
    MusterPr,
    MusterThis,
    PickJob,
    Summon,
    Survey,
)
from cabinet.pacts.healing import (
    Checked,
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
from cabinet.pacts.project import HEAL_NEEDS, Project
from cabinet.pacts.pulls import PullRequest, Watched
from cabinet.pacts.scm import ScmError
from cabinet.pacts.services import services

_RunT = TypeVar("_RunT", bound=Run)


# What every heal ritual's body makes of its components: the first step's
# payload, working `tasks`, or every task where none is named. Whether anybody
# is there to ask is vekna's to say.
def mustered(kind: type[_RunT], components: Heal, *tasks: Task) -> _RunT:
    return kind(
        project=services().project(HEAL_NEEDS),
        bound=components.bound,
        attended=attended(),
        batch=components.batch,
        tasks=components.working(*tasks),
    )


# Before the first fetch: an ssh remote would ask for a passphrase on a
# terminal no command under a cast has, and the answer is a config line. The
# run comes back already marked with whether the listing was cut short, so no
# exit can drop that.
async def _listed(run: _RunT) -> tuple[_RunT, list[PullRequest]]:
    await services().scm(run.project).preflight()
    listing = await services().forge(run.project).pulls()
    return run.listed(listing), listing.pulls


# Queued, with every step that works no branch spoken for now that the queue
# is known.
def _queued(run: Run, queue: list[PullRequest], kind: type[_RunT]) -> _RunT:
    opening = services().steps.opening(len(queue))
    return run.but(queue=queue).spoke_for(opening).to(kind)


# Every open pull request of yours the forge lists, bar the parked ones.
@step
async def muster_mine(run: MusterMine) -> Chart | Summon:
    try:
        run, pulls = await _listed(run)
    except (ScmError, ForgeError) as error:
        return run.but(stopped=str(error)).to(Chart)
    queue = services().pulls.wanted(pulls, run.project)
    return _queued(run, queue, Summon)


# The open pull request of yours for the branch at the cwd.
@step
async def muster_this(run: MusterThis) -> Chart | Survey:
    try:
        run, pulls = await _listed(run)
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
        run, pulls = await _listed(run)
    except (ScmError, ForgeError) as error:
        return run.but(stopped=str(error)).to(Chart)
    if not (queue := services().pulls.numbered(pulls, mustering.number)):
        stopped = f"no open pull request of yours is #{mustering.number}"
        return run.but(stopped=stopped).to(Chart)
    return _queued(run, queue, Survey)


# The base itself, where a configured job is red on it and no fix of yours is
# open: a branch cut from the base as the remote has it, handed straight to
# the job loop. No rerun first: `rerun_jobs` counts a check's runs on the
# pull request's branch, and this branch has none.
@step
async def muster_main(run: MusterMain) -> Chart | PickJob:
    project = run.project
    try:
        run, red = await _base_read(run)
        if not (red and run.tasks):
            return run.to(Chart)
        if dirty := await uncommitted(project):
            return run.but(stopped=dirty).to(Chart)
        branch = await _fix_cut(project)
    except (ScmError, ForgeError) as error:
        return run.but(stopped=str(error)).to(Chart)
    title = f"fix: make {project.base} green"
    pull = PullRequest.unopened(branch, project.base, title)
    return Work(run=run, pr=pull, red=red).one_per_job().to(PickJob)


# The configured jobs red on the base, said on one line as a pull request's
# todos are. None while a fix of yours is open: one fix at a time.
async def _base_read(run: MusterMain) -> tuple[MusterMain, list[Watched]]:
    project = run.project
    run, pulls = await _listed(run)
    if fixing := services().pulls.fixing(pulls, project):
        fix = fixing[0]
        emit_delta(
            f"a fix for {project.base} is already open: #{fix.number} {fix.branch}"
        )
        return run, []
    board = await services().forge(project).board(project.base)
    row = services().todos.base(board, project)
    emit_delta(services().report.surveyed(row))
    return run.but(surveyed=[row]), row.red


# Stand on the fix branch, cut from the base as the remote has it now.
async def _fix_cut(project: Project) -> str:
    scm = services().scm(project)
    base = f"{project.remote}/{project.base}"
    await scm.fetch()
    branch = project.fix_branch(await scm.head(base))
    await scm.branch(branch, base)
    return branch


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
# this cast takes no branch and asks for no share. Queued here and awaited
# in `attend`: awaiting each as it is queued would run them one at a time.
# Every component is passed on as this cast took it, so the children work the
# way the parent was asked to; `--unattended` reaches them through vekna.
@step
async def summon(run: Summon) -> Attend | Summon:
    if not run.queue:
        return run.to(Attend)
    pull = run.queue[0]
    row = await _surveyed(run.project, pull)
    emit_delta(services().report.surveyed(row))
    after = run.took(row)
    if isinstance(row, Unsurveyed) or not after.worked(row.todos):
        return after.to(Summon)
    asked = HealPr(number=pull.number, bound=run.bound, batch=run.batch)
    try:
        cast = await enqueue("heal.pr", asked)
    except NoDaemonError as error:
        stopped = (
            f"heal.mine queues a cast per pull request and needs the daemon: {error}"
        )
        # Casts already handed off keep running: `attend` gives each a row.
        return after.but(stopped=stopped).to(Attend)
    return after.summoned(Queued(pr=pull, cast=cast)).to(Summon)


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
# than raising where it happened.
@step
def chart(run: Chart) -> Done[Healed]:
    if run.has_news():
        emit_delta(services().report.healed(run))
    if run.failed():
        # The rows above name the branches; the error only counts them.
        raise RitualError(run.stopped or f"branches blocked: {len(run.blocked())}")
    return Done(
        Healed(
            surveyed=run.surveyed,
            checked=run.checked,
            not_reached=[pull.branch for pull in run.queue],
        )
    )


# `heal.mine` stays until every cast it queued has ended, and takes their rows
# for its own report. One wait at a time, in the order queued: the casts run
# side by side whichever is waited on, and a resumed cast replays the waits in
# the order it made them. A cast that failed took its rows with it, so the
# branch is blocked on what vekna said of the ending. With the daemon gone
# the wait cannot be made, and the branch is blocked with its outcome unknown.
@step
async def attend(run: Attend) -> Chart:
    after = run
    for one in run.queued:
        try:
            healed = Healed.model_validate(await awaited(one.cast))
        except CastFailedError as error:
            healed = _blocked(one, str(error))
        except NoDaemonError as error:
            healed = _blocked(one, f"outcome unknown, the daemon is gone: {error}")
        after = after.merged(one, healed)
    return after.to(Chart)


def _blocked(one: Queued, note: str) -> Healed:
    row = Checked.of(one.pr, "blocked", unpushed=None, note=note)
    return Healed(checked=[row])
