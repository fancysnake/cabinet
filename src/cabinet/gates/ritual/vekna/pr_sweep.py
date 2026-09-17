"""Nighttime pull request maintenance, in two passes.

    vekna cast pr_refresh [--bound N]
    vekna cast pr_cover [--bound N]

Every pull request you have open is taken in turn, oldest-modified first, and
both passes take a branch the same way: the base branch is merged in, conflicts
are resolved, the work is pushed, and the report says how each branch ended.

``pr_refresh`` is the fast one, and it is the one to run over everything: it
merges the base in and makes the project's gate green — lint, types, the fast
suites — with no coverage measurement anywhere in it. Then it posts the quality
review, unless the branch already carries the reviewed label. A branch the
merge brought nothing to, and whose gate jobs CI is happy with, skips the gate:
the server has run it over that tree already.

Neither gate is re-run whole while a repair is underway. Where the runner names
the task that broke, the next round runs that task alone, and the gate itself
runs once more when it comes back green.

``pr_cover`` is the slow one, and it asks before it spends: it reads what CI
made of the branch — the check board, including the patch coverage the
coverage service's own check carries — and, where coverage or the suite is
unhappy, runs the project's coverage task, writes the tests for what the branch
left uncovered, and repairs the suite where it is the suite that is broken.
Between rounds it re-measures with the fast coverage task; the full one runs
again at the end, and that is the one that counts. It posts no review: the fast
pass runs first and that one is where the review comes from.

A branch is left alone rather than reported broken when the checkout will not go
through, which is what another worktree standing on it looks like. Checking out
the base branch is not the same thing — nothing below it can run at all — so
that one still ends the run.

What neither pass does is read the review one of them posted. Answering one is
somebody's decision and this runs at 3am with nobody to ask, so every action
item stays an open thread and ``pr_review`` goes through them with you in the
morning.

A branch the gates would not go green on is still reviewed. It stands down
rather than stopping: the worktree is released, so the reading happens on the
last commit that was any good, and then it is reviewed like any other before
being reported blocked. The slow pass stands a branch down the same way and
reviews nothing, as it never does.

A pull request wearing the wait label is left alone entirely: it is dropped at
the listing, so nothing checks it out and it appears nowhere in the report.

Each pass marks its checkpoint on the board: the branch earns the ``started``
checkpoint the moment the merge begins, and ``done`` only where it comes out
green — the two are exclusive, so adding one takes the other off.

The review is one inline comment per action item, anchored to the code it is
about, and the branch is labelled once it is posted. That label is the only
thing standing between a branch and another review: drop it after changing the
branch meaningfully, and the next run reviews it again. A blocked branch's
review is provisional, and the label goes on all the same.

Both run unattended, so they ask you nothing: at 3am a prompt is a hang, so the
budgets take that decision instead. Agents still work permissively inside a
step, and what holds them is the step boundary — a gate is green or it is not,
a budget is spent or it is not — and the allowlist: no agent here commits,
pushes, runs a sweep, or speaks to the forge.

Two things end the whole run rather than one branch: a worktree that is not
clean, and an agent that dies mid-flight. Both still print the report first,
then fail the cast.

Budgets are per step and per branch: a step may be retried ``--bound`` times,
going green clears its count, and moving to the next pull request clears them
all. A verdict a step already gave up on once is not paid for twice — the next
branch whose gate says the same thing stands down without spending its budget.
"""

from typing import TYPE_CHECKING, NamedTuple

from vekna.lexicon import RitualError, Transition, done, emit_delta, goto, ritual, step

from cabinet.pacts.agent import Fallen, Misread
from cabinet.pacts.forge import ForgeError
from cabinet.pacts.pulls import Board, Closed, PrSweep, Report, Run, Work, joined
from cabinet.pacts.scm import ScmError
from cabinet.pacts.services import services
from cabinet.pacts.threads import Finding, Findings

if TYPE_CHECKING:
    from cabinet.pacts.project import State
    from cabinet.pacts.tasks import Ran

# The backstop, not the control — the per-step bounds are. Six pull requests
# through ~9 steps each, with three repair loops that may each burn two turns
# per `--bound`, comes to a little over 200 at the maximum bound; this sits
# above that, because tripping it costs the report as well as the run.
_MAX_STEPS = 240


# Merge the base in, make the gate green, push, review.
@ritual("pr_refresh", max_steps=_MAX_STEPS)
def pr_refresh(components: PrSweep) -> Transition:
    project = services().project()
    return goto(list_prs, Run(project=project, bound=components.bound, mode="refresh"))


# Where CI is unhappy about coverage or tests, close the gap.
@ritual("pr_cover", max_steps=_MAX_STEPS)
def pr_cover(components: PrSweep) -> Transition:
    project = services().project()
    return goto(list_prs, Run(project=project, bound=components.bound, mode="cover"))


# Ask the forge what is open, and queue what the night will take.
@step
async def list_prs(run: Run) -> Transition:
    # Before the first fetch: an ssh remote would ask for a passphrase on a
    # terminal no command under a cast has, and the answer is a config line.
    try:
        await services().scm(run.project).preflight()
        pulls = await services().forge(run.project).pulls()
    except (ScmError, ForgeError) as error:
        return goto(report, run.but(stopped=str(error)))
    return goto(next_pr, run.but(queue=services().pulls.wanted(pulls, run.project)))


@step
def next_pr(run: Run) -> Transition:
    if not run.queue:
        return goto(report, run)
    pull, *rest = run.queue
    # A fresh Work per pull request, so no budget survives the branch change.
    return goto(check_clean, Work(run=run.but(queue=rest), pr=pull))


@step
async def check_clean(work: Work) -> Transition:
    try:
        dirty = await services().scm(work.run.project).status()
    except ScmError as error:
        return goto(report, work.abandoned(str(error)))
    if dirty:
        # Fatal by design: everything below this line moves branches around,
        # and doing that over someone's uncommitted work is how it gets lost.
        return goto(report, work.abandoned(f"the worktree is not clean:\n{dirty}"))
    return goto(sync_branch, work)


# Update the base branch, then stand on the branch as the remote has it.
@step
async def sync_branch(work: Work) -> Transition:
    scm = services().scm(work.run.project)
    pull = work.pr
    try:
        await scm.sync_base(pull.base)
    except ScmError as error:
        return goto(report, work.abandoned(str(error)))
    # On its own rather than chained to the rest, because the failures are
    # different answers: a checkout that will not go through is another
    # worktree standing on the branch, and that is nobody's fault.
    try:
        await scm.checkout(pull.branch)
    except ScmError as error:
        return goto(skip_pr, work.but(note=str(error)))
    try:
        await scm.catch_up(pull.branch)
    except ScmError as error:
        return goto(set_aside, work.but(note=str(error)))
    return goto(merge_base, work)


# Best-effort and never fatal: a checkpoint is a board marker, and losing one
# is not worth abandoning a merge that is about to happen. What the forge made
# of it comes back as the caller's note instead.
async def _mark(work: Work, state: State) -> str:
    project = work.run.project
    add, remove = services().checkpoint(project, work.run.mode, state)
    try:
        await services().forge(project).label(
            work.pr.number, add=[add], remove=[remove]
        )
    except ForgeError as error:
        return f"could not mark {add}: {error}"
    return ""


# Merge the base in, and say whether it brought anything with it.
@step
async def merge_base(work: Work) -> Transition:
    # The first step that changes the branch, so this is where the checkpoint
    # goes on: everything above only takes the branch.
    if note := await _mark(work, "started"):
        emit_delta(f"{work.pr.branch}: {note}")
    scm = services().scm(work.run.project)
    # Asked before the merge rather than read off it afterwards: git says
    # "Already up to date" in whatever language the terminal is set to.
    contained = await scm.contains(work.pr.base)
    merged = await scm.merge(work.pr.base)
    if merged.exit_code == 0:
        return goto(take_pass, work.graded(unchanged=contained))
    # The index is read once, by the step below. What this carries there is
    # why the merge failed, for the one case that is not a conflict at all.
    said = services().verdicts.said(merged)
    return goto(resolve_conflicts, work.merging_on(f"git merge failed: {said}"))


# Hand the conflicted files to an agent until the index comes back clean.
@step
async def resolve_conflicts(work: Work) -> Transition:
    project = work.run.project
    try:
        unmerged = await services().scm(project).unmerged()
    except ScmError as error:
        return goto(set_aside, work.but(note=str(error)))
    if not unmerged:
        # Nothing conflicted and nothing tried yet: the merge failed for a
        # reason no agent can fix, and the note says which.
        if not work.spent(resolve_conflicts.name):
            return goto(set_aside, work.but(note=f"no conflicts: {work.note}"))
        return goto(take_pass, work.but(note="").cleared(resolve_conflicts.name))
    if work.exhausted(resolve_conflicts.name):
        stopped = work.stopped_by("the merge conflicts were not resolved")
        return goto(stand_down, stopped)
    prompt = services().prompts.resolve(
        project, base=work.pr.base, branch=work.pr.branch, files="\n".join(unmerged)
    )
    fallen = (
        await services()
        .agent(project)
        .ask(prompt, role="resolver", key=f"merge-{work.pr.number}")
    )
    if fallen:
        return goto(report, work.abandoned(fallen.reason))
    # Back through this same step, which re-reads git rather than believing
    # the agent. The note goes now: past here the merge failing is just what a
    # conflict looks like, and the row is not to be told about it twice.
    return goto(resolve_conflicts, work.but(note="").charged(resolve_conflicts.name))


# What CI says about the branch as it stands, or None where the forge would
# not say — which every reader takes as "nobody has said it is fine".
async def _board(work: Work) -> Board | None:
    try:
        return await services().forge(work.run.project).board(work.pr.branch)
    except ForgeError:
        return None


# The first of the three places the two passes part. The fast one owes the gate
# green before it commits the merge; the slow one owes nothing there — its own
# gate runs the fast suites anyway. The fast one also owes nothing where the
# merge brought nothing in and CI's own gate jobs are green: that is the same
# tree the server already ran the gate over.
@step
async def take_pass(work: Work) -> Transition:
    if work.run.mode != "refresh":
        return goto(finish_merge, work)
    if work.unchanged:
        board = await _board(work)
        if board is not None and services().pulls.gates_green(board, work.run.project):
            note = "nothing to merge, and CI ran the gate green"
            return goto(finish_merge, work.but(note=note))
    return goto(gate_check, work)


# Run the gate, and repair it until it is green or the budget is gone.
@step
async def gate_check(work: Work) -> Transition:
    project = work.run.project
    verdicts = services().verdicts
    # The task that broke last time round, where the runner named one: an
    # agent working on one linter is judged by that linter, not by the whole
    # chain in front of it.
    gate = work.gate or project.gate
    ran = await services().tasks(project).run(gate)
    if ran.exit_code == 0:
        # A task passing on its own is not the gate passing — it is the reason
        # to spend the gate. The whole chain runs once more.
        if gate != project.gate:
            return goto(gate_check, work.but(gate=""))
        return goto(finish_merge, work.but(gate="").cleared(gate_check.name))
    said_now = verdicts.verdict(ran)
    # Asked before the first repair and not after, so this reads "the branch
    # arrived broken the same way", never "the agent failed to fix it twice".
    if not work.spent(gate_check.name) and verdicts.already_seen(
        said_now, work.run.seen
    ):
        reason = f"`{gate}` is red as it already was:\n{said_now}"
        return goto(stand_down, work.stopped_by(reason))
    if work.exhausted(gate_check.name):
        seen = work.run.but(seen=[*work.run.seen, said_now])
        reason = f"`{gate}` is still red:\n{said_now}"
        return goto(stand_down, work.stopped_by(reason).but(run=seen))
    prompt = services().prompts.fix_gates(project, verdicts.said(ran), gate=gate)
    fallen = (
        await services()
        .agent(project)
        .ask(prompt, role="writer", key=f"gates-{work.pr.number}")
    )
    if fallen:
        return goto(report, work.abandoned(fallen.reason))
    narrowed = work.but(gate=verdicts.narrowed(ran))
    return goto(gate_check, narrowed.charged(gate_check.name))


# Close an open merge and commit whatever the repairs left behind.
@step
async def finish_merge(work: Work) -> Transition:
    scm = services().scm(work.run.project)
    if work.merging:
        try:
            await scm.continue_merge()
        except ScmError as error:
            return goto(set_aside, work.but(note=str(error)))
    # A clean merge leaves the gate repairs uncommitted, and a merge the agent
    # committed itself leaves them behind too. Either way this is where they
    # land — and it is a no-op when there is nothing to land.
    try:
        await scm.commit(f"chore: merge {work.pr.base} and fix the gates")
    except ScmError as error:
        return goto(set_aside, work.but(note=f"could not commit the merge: {error}"))
    merged = work.merged()
    # Coverage runs on this side of the merge and the gate on the other: what
    # the gate repairs belongs in the merge commit above, while the tests the
    # slow pass writes are a commit of their own.
    if work.run.mode == "cover":
        return goto(check_ci, merged)
    return goto(push_work, merged)


# Asked of the pull request rather than measured here, because measuring is
# the hour this pass is trying not to spend. Anything less than a clear yes —
# a check that has not reported, a board the forge would not give — buys the
# run rather than the skip.
# Ask CI whether this branch is worth the slow gate.
@step
async def check_ci(work: Work) -> Transition:
    board = await _board(work)
    if board is None or services().pulls.wants_cover(board, work.run.project):
        return goto(cover, work)
    return goto(push_work, work.but(note="coverage and the suite are green on CI"))


# Close the coverage gap, repairing a red suite like any other gate.
@step
async def cover(work: Work) -> Transition:
    project = work.run.project
    verdicts = services().verdicts
    # The first measurement is the whole thing, because it is the one that
    # decides whether there is a gap at all. What a repair round re-runs is
    # the fast half, or the single task that broke.
    gate = work.gate or project.coverage
    measured = await services().tasks(project).run(gate)
    output = verdicts.coverage_report(measured)
    missing = verdicts.uncovered(output)
    if not missing and measured.exit_code == 0:
        # Anything but the full measurement is a reason to spend the full
        # measurement, not a branch that is covered.
        if gate != project.coverage:
            return goto(cover, work.but(gate=""))
        # Only where tests were actually written: most branches pass here
        # first time, and a commit rite that never commits is noise.
        if work.spent(cover.name):
            try:
                await services().scm(project).commit(
                    "test: cover the lines this branch changes"
                )
            except ScmError as error:
                note = f"could not commit the tests: {error}"
                return goto(set_aside, work.but(note=note))
        return goto(push_work, work.but(gate="").cleared(cover.name))
    said_now = verdicts.verdict(measured)
    repair = _repair(work, gate=gate, measured=measured, output=output, missing=missing)
    # Against what the run knew on the way in, never `repair.run`: that one
    # has this verdict in it already and would recognise nothing but itself.
    seen_already = (
        not missing
        and not work.spent(cover.name)
        and verdicts.already_seen(said_now, work.run.seen)
    )
    if seen_already or work.exhausted(cover.name):
        reason = (
            f"`{gate}` failed as it already did:\n{said_now}"
            if seen_already
            else f"`{gate}` {repair.left}:\n{said_now}"
        )
        stopped = work.stopped_by(reason)
        return goto(
            stand_down, stopped if seen_already else stopped.but(run=repair.run)
        )
    fallen = (
        await services()
        .agent(project)
        .ask(repair.asking, role="writer", key=f"cover-{work.pr.number}")
    )
    if fallen:
        return goto(report, work.abandoned(fallen.reason))
    return goto(cover, work.but(gate=repair.next_gate).charged(cover.name))


class _Repair(NamedTuple):
    left: str
    asking: str
    run: Run
    next_gate: str


# Two different jobs down one budget, because they are the same step going
# round: lines left uncovered are written up as tests, and a suite that will
# not pass at all is repaired like any other red gate. Only a red suite is
# worth remembering across the night: what lines a branch left uncovered is
# that branch's own business, and two of them missing lines in the same file
# look identical from here.
def _repair(
    work: Work, *, gate: str, measured: Ran, output: str, missing: bool
) -> _Repair:
    project = work.run.project
    verdicts = services().verdicts
    if missing:
        # Lines are re-measured without the slow suites: what an agent writes
        # here is a test, and the fast suite is the one that runs it.
        return _Repair(
            left="still reports missing lines",
            asking=services().prompts.cover_gap(
                project, output, partial=gate != project.coverage
            ),
            run=work.run,
            next_gate=project.fast_coverage,
        )
    # A suite that will not run is repaired against the task that would not
    # run, where the runner named one.
    return _Repair(
        left="is still red",
        asking=services().prompts.fix_gates(
            project, verdicts.said(measured), gate=gate
        ),
        run=work.run.but(seen=[*work.run.seen, verdicts.verdict(measured)]),
        next_gate=verdicts.narrowed(measured) or project.fast_coverage,
    )


# Not fatal, and not `set_aside`: a push that will not go through costs the
# review its anchors and nothing else, and that is worth more than a branch
# dropped for the night. What is left behind is said twice over: in this note,
# and in the row's `unpushed`, counted off git at the end.
@step
async def push_work(work: Work) -> Transition:
    try:
        await services().scm(work.run.project).push(work.pr.branch)
    except ScmError as error:
        work = work.but(note=joined(work.note, str(error)))
    # The review belongs to the fast pass, which runs first and over
    # everything. A branch reaching the slow one already carries whatever
    # review it is going to get.
    if work.run.mode == "cover":
        return goto(finish_pr, _ended(work))
    return goto(quality_review, work)


# What the review says is not the night's to have an opinion about — the
# outcome is the gates' answer, and `pr_review` answers the review.
def _ended(work: Work) -> Closed:
    return Closed(work=work, outcome="blocked" if work.blocked else "green")


# The one step with no budget and no loop, because there is nothing here to
# retry against. An agent that found nothing to post is indistinguishable from
# one that read badly, so the label goes on either way, and a review that came
# out empty is yours to notice and ask for again by taking it off.
# Post the review, unless the branch already carries the label.
@step
async def quality_review(work: Work) -> Transition:
    project = work.run.project
    forge = services().forge(project)
    number = work.pr.number
    try:
        labels = await forge.labels(number)
        # An earlier night's review, which is not this night's work to label.
        if project.labels.reviewed in labels:
            return goto(finish_pr, _ended(work))
        threads = await forge.threads(number)
    except ForgeError as error:
        return goto(set_aside, work.but(note=str(error)))
    prompt = services().prompts.review(
        project, base=work.pr.base, threads=threads, reason=work.reason
    )
    read = (
        await services()
        .agent(project)
        .ask_for(prompt, output=Findings, role="reader", key=f"review-{number}")
    )
    if isinstance(read, Fallen):
        return goto(report, work.abandoned(read.reason))
    if isinstance(read, Misread):
        return goto(set_aside, work.but(note=read.reason))
    # Every item opens with the review's title, so it can be told from anyone
    # else's comment — and answered by `pr_review` as one.
    try:
        for finding in read.items:
            body = f"## {project.review_title}\n\n{finding.body}"
            await forge.comment(
                number, Finding(path=finding.path, line=finding.line, body=body)
            )
        await forge.label(number, add=[project.labels.reviewed])
    except ForgeError as error:
        return goto(set_aside, work.but(note=f"the review did not all go up: {error}"))
    return goto(finish_pr, _ended(work))


# Write the branch's row into the run, and go on to the next one.
@step
async def finish_pr(closed: Closed) -> Transition:
    work = closed.work
    # Only a green branch is done.
    marked = await _mark(work, "done") if closed.outcome == "green" else ""
    row = work.checked(
        closed.outcome,
        # Asked of git rather than tracked in the payload: what needs pushing
        # is what the remote has not got, whoever put it there.
        unpushed=await services().scm(work.run.project).ahead(work.pr.branch),
        note=work.telling(marked),
    )
    return goto(next_pr, work.run.rowed(row))


# What comes back is this act's own bookkeeping and nothing else — the callers
# join it to whatever else the row is carrying.
async def _released(work: Work) -> str:
    try:
        stashed = await services().scm(work.run.project).release(work.pr.branch)
    except ScmError as error:
        return str(error)
    return f'stashed as "{stashed}"' if stashed else ""


# A branch that will not go green is not a branch that cannot be read, so it
# takes the same reading every other pull request gets. The worktree goes back
# first: half a repair is not something to review.
@step
async def stand_down(work: Work) -> Transition:
    return goto(push_work, work.standing_down(await _released(work)))


# Nothing to release and nothing to count: this is only reached where the
# checkout itself would not go through, so the worktree never moved and the
# branch is exactly as its owner left it.
# Leave the branch where it is, and say so in the report.
@step
def skip_pr(work: Work) -> Transition:
    row = work.checked("skipped", unpushed=None, note=work.telling())
    return goto(next_pr, work.run.rowed(row))


# Give the worktree back and report the branch blocked.
@step
async def set_aside(work: Work) -> Transition:
    # The worktree goes back before the count, not as an argument alongside
    # it: what is left to push is asked of a tree this step has finished with.
    released = await _released(work)
    row = work.checked(
        "blocked",
        unpushed=await services().scm(work.run.project).ahead(work.pr.branch),
        # A branch that stood down and then failed one of the reading steps
        # arrives here with two things to say, and the second must not cost
        # it the first: the morning needs to hear the red gate.
        note=work.telling(released),
    )
    return goto(next_pr, work.run.rowed(row))


# Nothing to await: this routes and renders. The summary is emitted before the
# failure is raised, which is the whole reason every ending routes here rather
# than raising where it happened.
@step
def report(run: Run) -> Transition:
    emit_delta(services().report.sweep(run))
    if run.stopped:
        raise RitualError(run.stopped)
    return done(
        Report(
            checked=run.checked,
            not_reached=[pull.branch for pull in run.queue],
            failed=run.stopped,
        )
    )
