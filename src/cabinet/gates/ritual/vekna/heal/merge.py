"""The merge task: the base merged in, and the gate made green over it."""

from vekna.lexicon import step

from cabinet.gates.ritual.vekna.heal.repair import asked, repaired
from cabinet.pacts.heal import (
    Chart,
    FinishMerge,
    GateCheck,
    MergeBase,
    ResolveConflicts,
    SetAside,
    StandDown,
    Tend,
)
from cabinet.pacts.project import CiJob
from cabinet.pacts.scm import ScmError
from cabinet.pacts.services import services


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
    if work.exhausted(resolve_conflicts.name):
        stopped = work.stopped_by("the merge conflicts were not resolved")
        return stopped.to(StandDown)
    prompt = services().prompts.resolve(
        project, base=work.base_ref, branch=work.pr.branch, files="\n".join(unmerged)
    )
    escalated = services().sizes.escalates(
        conflicts=len(unmerged), spent=work.spent(resolve_conflicts.name)
    )
    if fallen := await asked(work, prompt, key="merge", escalated=escalated):
        return work.abandoned(fallen.reason).to(Chart)
    # Back through this same step, which re-reads git rather than believing
    # the agent. The note goes now: past here the merge failing is just what a
    # conflict looks like, and the row is not to be told about it twice.
    return work.but(note="").charged(resolve_conflicts.name)


# Run the gate, and repair it until it is green or the budget is gone.
@step
async def gate_check(work: GateCheck) -> GateCheck | FinishMerge | StandDown | Chart:
    against = CiJob(gate=work.run.project.gate)
    return await repaired(work, against, name=gate_check.name, then=FinishMerge)


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
