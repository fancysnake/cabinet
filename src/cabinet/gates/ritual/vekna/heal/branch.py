"""Taking a branch, handing it each task, and leaving it.

A branch with a task this cast works is taken: the worktree must be
clean, the remote is fetched, and the branch is checked out and fast-forwarded
to it. The base is only ever read as the remote has it: a pooled worktree
cannot stand on a base the tree it was made from is standing on. Then
``tend`` hands the branch each task in turn, and every task ends back at
``tend``.

A branch whose checkout will not go through is blocked, and so fails the cast:
that is what another worktree standing on it looks like, and its owner is told
to move off it. A fetch that fails ends the cast, with every branch after it.

What a cast committed and has not pushed goes up before the branch is left.
Nothing waits for CI after a push, and nothing merges a branch that is merely
behind.
"""

from typing import TypeAlias

from vekna.lexicon import step

from cabinet.pacts.forge import ForgeError
from cabinet.pacts.heal import (
    Chart,
    CheckClean,
    FinishPr,
    MergeBase,
    OpenPull,
    PostGuide,
    PushWork,
    QualityReview,
    RerunJobs,
    Resurvey,
    SetAside,
    SettleLeft,
    StandDown,
    Survey,
    SyncBranch,
    Tend,
)
from cabinet.pacts.healing import Task, Work
from cabinet.pacts.project import Project
from cabinet.pacts.scm import ScmError
from cabinet.pacts.services import services


# What stands in the way of moving branches around, or nothing: everything
# that moves one does it over someone's uncommitted work otherwise, and that is
# how it gets lost.
async def uncommitted(project: Project) -> str:
    dirty = await services().scm(project).status()
    return f"the worktree is not clean:\n{dirty}" if dirty else ""


@step
async def check_clean(work: CheckClean) -> Chart | SyncBranch:
    try:
        dirty = await uncommitted(work.run.project)
    except ScmError as error:
        return work.abandoned(str(error)).to(Chart)
    if dirty:
        # Fatal by design.
        return work.abandoned(dirty).to(Chart)
    return work.to(SyncBranch)


# Fetch, then stand on the branch as the remote has it.
@step
async def sync_branch(work: SyncBranch) -> Chart | SetAside | Tend:
    scm = services().scm(work.run.project)
    pull = work.pr
    try:
        await scm.fetch()
    except ScmError as error:
        return work.abandoned(str(error)).to(Chart)
    try:
        await scm.checkout(pull.branch)
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


# Hand the branch its next task, or have it surveyed again once none is left.
# Whatever this cast committed is pushed first: every task after the merge
# works on code the forge has, and a branch is not left with commits only this
# worktree holds.
@step
def tend(work: Tend) -> PushWork | OpenPull | Resurvey | _First:
    opened = work.pr.is_opened
    # `heal.main`'s branch has no pull request until `open_pull` makes one, and
    # pushes it then: a branch that stood down must not land on the remote as a
    # copy of the base.
    if work.changed and opened:
        return work.to(PushWork)
    if not work.todos:
        return work.to(Resurvey) if opened else work.to(OpenPull)
    task, *rest = work.todos
    taken = work.but(todos=rest)
    return taken.to(_FIRST[task])


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


# `heal.main`'s branch: push it, then open its pull request, which `heal.mine`
# tends from here on. The push is repeated here because a branch reused from an
# earlier cast can hold commits the remote never got, with no new one to send
# it through `push_work`. A blocked branch is opened too, so the next
# `heal.main` finds a fix under way, and the pull request says what stopped it.
# A branch with no commit past the base has nothing to open.
@step
async def open_pull(work: OpenPull) -> FinishPr:
    project = work.run.project
    pull = work.pr
    found = f"`heal.main` found `{pull.base}` red and worked on it on this branch."
    body = "\n\n".join(part for part in (found, work.telling()) if part)
    try:
        scm = services().scm(project)
        if not await scm.beyond(work.base_ref):
            left = "nothing was committed, so no pull request was opened"
            return work.noting(left).to(FinishPr)
        await scm.push(pull.branch)
        opened = (
            await services()
            .forge(project)
            .open_pull(pull.branch, pull.base, title=pull.title, body=body)
        )
    except (ScmError, ForgeError) as error:
        return work.noting(str(error)).to(FinishPr)
    return work.opened(opened.number, opened.url).noting(opened.url).to(FinishPr)


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
