"""The ci task: each red job rerun or fixed, one check at a time."""

from typing import TypeVar

from vekna.lexicon import step

from cabinet.gates.ritual.vekna.heal.repair import asked, repaired
from cabinet.pacts.forge import ForgeError
from cabinet.pacts.heal import (
    Chart,
    CloseGap,
    JobGate,
    LandJob,
    MendJob,
    PickJob,
    RerunJobs,
    SetAside,
    StandDown,
    Tend,
)
from cabinet.pacts.healing import Work
from cabinet.pacts.project import CiJob
from cabinet.pacts.scm import ScmError
from cabinet.pacts.services import services

_WorkT = TypeVar("_WorkT", bound=Work)


# A job loop's name for the check in hand: the budget it spends, and the
# session every round continues, from the mend that read the log through the
# gate. The next job starts on a session of its own.
def _loop(work: Work, name: str) -> str:
    return f"{name}-{work.in_hand.check.name}"


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
    for red in work.red:
        check = red.check
        if not red.job.rerun:
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
    if work.in_hand.job.covering:
        return work.to(CloseGap)
    return work.to(MendJob)


# The agent reads how the job failed on CI and fixes it. A job with a gate
# then goes round the repair loop against it, in the same session; one without
# is committed as the agent left it, and the push is what checks it.
@step
async def mend_job(work: MendJob) -> PickJob | JobGate | LandJob | Chart:
    project = work.run.project
    check = work.in_hand.check
    gate = work.in_hand.job.gate
    try:
        log = await services().forge(project).log(check)
    except ForgeError as error:
        # The gate can still find what the log would have said.
        if gate:
            return work.noting(str(error)).to(JobGate)
        return work.passed_over(str(error)).to(PickJob)
    prompt = services().prompts.fix_job(
        project, services().verdicts.logged(log), job=check.name, gate=gate
    )
    escalated = services().sizes.escalates(red=len(work.red))
    if fallen := await asked(
        work, prompt, key=_loop(work, job_gate.name), escalated=escalated
    ):
        return work.abandoned(fallen.reason).to(Chart)
    return work.to(JobGate) if gate else work.to(LandJob)


# A job's repair loop. Standing down ends the ci task, so the checks still
# behind the one in hand are named rather than carried off unread.
async def _mended(
    work: _WorkT, against: CiJob, *, name: str
) -> LandJob | _WorkT | StandDown | Chart:
    went = await repaired(work, against, name=name, then=LandJob)
    return went.leaving_red() if isinstance(went, StandDown) else went


# The job's gate, repaired until it is green: the merge's loop, run against
# the job's own commands.
@step
async def job_gate(work: JobGate) -> JobGate | LandJob | StandDown | Chart:
    return await _mended(work, work.in_hand.job, name=_loop(work, job_gate.name))


# Close the coverage gap, repairing a red suite like any other gate. The first
# measurement is the whole one, because it decides whether there is a gap at
# all; a repair round re-runs the fast one, or the single task that broke.
@step
async def close_gap(work: CloseGap) -> CloseGap | LandJob | StandDown | Chart:
    # Anything but the full measurement is a reason to spend the full
    # measurement, not a branch that is covered.
    return await _mended(work, work.in_hand.job, name=_loop(work, close_gap.name))


# Each job's fix is a commit of its own. A fix that changed nothing is no
# commit at all, and no fix either: green here and red on CI, the job is left
# red and the row says so.
@step
async def land_job(work: LandJob) -> PickJob | SetAside:
    name = work.in_hand.check.name
    message = (
        "test: cover the lines this branch changes"
        if work.in_hand.job.covering
        else f"fix: make the {name} job green"
    )
    try:
        committed = await services().scm(work.run.project).commit(message)
    except ScmError as error:
        return work.noting(f"could not commit the {name} fix: {error}").to(SetAside)
    if not committed:
        return work.passed_over(f"`{name}` passes here; CI is still red").to(PickJob)
    return work.landed().to(PickJob)
