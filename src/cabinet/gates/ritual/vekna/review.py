"""Answer the reviews `refresh` left on your branches, then ship them.

    vekna cast review [--bound N] [--batch N]

The follow-up to `refresh`, and its opposite: nothing done without you saying
so, and it is what commits the result.

A branch is a candidate when its pull request is open, yours, wearing the
reviewed label, not wearing the wait label, and carrying a review thread nobody
has settled. They are taken one after another, longest-waiting first — except
that the branch you are standing on goes first, which is also what keeps two
terminals on two branches off each other's work. A branch whose checkout will
not go through is reported and the next one is offered.

Each branch is asked about as its turn comes, and saying no to one moves on to
the next rather than ending the cast. The count of what is still open is asked
per branch, when its turn comes: the sweeps run alongside this and a branch's
threads can be settled while the cast is standing on another one.

The triage is read rather than fetched: the ritual fetches the open threads,
fences them as data, and an agent reads them against the code as it stands and
hands back one item per thread, with a priority and what it would do about it.
That goes on your terminal and nowhere else, and the threads are untouched
until you have been through them.

You answer the items one at a time, in your own words; saying nothing takes the
reading's own proposal. One agent then fixes what you said to fix and writes a
reply for every item — and the ritual, which is the only thing here that can
reach the forge, opens the issues you said to file, posts the replies, and
settles the threads.

A branch with more open threads than ``--batch`` goes round in batches: the
first ``--batch`` are read, answered and settled, and the next round fetches
what the forge still holds open. The gate runs once, after the last round, so
a forty-thread review is six triages you can hold in your head and one commit.

The branch earns the ``started`` checkpoint the moment the agent is turned
loose on the triage, and ``done`` once nothing is left open. A branch left with
threads still open, or one a gate stopped, keeps ``started``.

Then the gate runs, is repaired up to ``--bound`` times, and what came out is
committed and pushed — no question in between, because the answers you gave
were the decision. Diff coverage is not measured here — that is ``cover``.

A gate that will not go green after ``--bound`` attempts ends the cast rather
than moving on: the repair work is sitting uncommitted in the worktree, and
taking another branch would either commit it there or throw it away.
"""

from vekna.folio.flow import decide
from vekna.lexicon import RitualError, Transition, done, emit_delta, goto, step

from cabinet.gates.ritual.vekna.marking import mark
from cabinet.pacts.agent import Fallen, Misread
from cabinet.pacts.forge import ForgeError
from cabinet.pacts.project import State
from cabinet.pacts.repairs import Attempt, Fixed, Stalled
from cabinet.pacts.reviews import (
    Answering,
    Branch,
    Instructed,
    Landing,
    Picking,
    Triage,
)
from cabinet.pacts.scm import ScmError
from cabinet.pacts.services import services
from cabinet.pacts.threads import Answered, Thread, TriageNotes

# One thread for every agent call in the cast, so a later round meets an agent
# that remembers writing the one before.
_THREAD = "review"


# A branch's turn ending the whole cast. Nothing here raises: `recap` owes the
# report however the cast ends, and it is `recap` that fails it afterwards.
# The row says which branch was in flight, because the reason often does not.
def _stopped(branch: Branch, reason: str) -> Transition:
    return goto(recap, branch.rowed("stopped", reason).but(stopped=reason))


# Ask the forge which of your branches carry a review, and queue them.
@step
async def queue_up(picking: Picking) -> Transition:
    project = picking.project
    scm = services().scm(project)
    try:
        await scm.preflight()
        pulls = await services().forge(project).pulls()
        mine = await scm.here()
    except (ScmError, ForgeError) as error:
        # No branch has been taken yet, so there is no row to write — only the
        # report, which is owed even when it says nothing.
        return goto(recap, picking.but(stopped=str(error)))
    # Reviewed by the night and not yet answered: the reviewed label says a
    # review was posted, and whether it is still waiting is asked branch by
    # branch in `pick`. Never the base branch, whatever the forge says: this
    # ritual ends in a commit and a push on the branch it takes.
    carrying = [
        pull
        for pull in services().pulls.wanted(pulls, project)
        if pull.branch != project.base and pull.wears(project.labels.reviewed)
    ]
    # You have just finished working on this branch and its review is what you
    # sat down for. The rest follow oldest-modified first.
    ordered = [pull for pull in carrying if pull.branch == mine] + [
        pull for pull in carrying if pull.branch != mine
    ]
    return goto(pick, picking.but(queue=ordered))


# `None` where the forge would not say, which is not "nothing to do": `pick`
# skips that branch rather than calling it clean, and names it.
async def _open_threads(branch: Branch) -> int | None:
    try:
        threads = await services().forge(branch.project).threads(branch.number)
    except ForgeError:
        return None
    return sum(1 for thread in threads if not thread.resolved)


# Take the next branch whose review is still waiting.
@step
async def pick(picking: Picking) -> Transition:
    if not picking.queue:
        return goto(recap, picking)
    pull, *rest = picking.queue
    branch = Branch(
        picking=picking.but(queue=rest), name=pull.branch, number=pull.number
    )
    if (left := await _open_threads(branch)) is None:
        emit_delta(f"the forge would not say what is open on {branch.name}")
        return goto(pick, branch.rowed("unread"))
    if not left:
        # The ordinary case, and the reason it earns no row.
        return goto(pick, branch.picking)
    # Fatal, and before every checkout: `look` moves branches around and later
    # commits everything it finds, so work left in the tree would be committed
    # onto the branch it takes.
    try:
        dirty = await services().scm(branch.project).status()
    except ScmError as error:
        return _stopped(branch, str(error))
    if dirty:
        return _stopped(branch, f"the worktree is not clean:\n{dirty}")
    return goto(look, branch)


# Check the branch out.
@step
async def look(branch: Branch) -> Transition:
    # Asked before the checkout: a `no` from the other side of the move leaves
    # you standing on a branch you did not ask for.
    if not await decide(f"read the review on {branch.name}?"):
        return goto(pick, branch.rowed("declined"))
    # Not fatal, unlike every other command here: a checkout that will not go
    # through is another worktree standing on the branch, and there is a whole
    # list of other pull requests this could be reading instead.
    try:
        await services().scm(branch.project).checkout(branch.name)
    except ScmError as error:
        emit_delta(f"{branch.name} is checked out elsewhere: {error}")
        return goto(pick, branch.rowed("elsewhere", str(error)))
    return goto(read, branch)


async def _unsettled(branch: Branch) -> list[Thread]:
    threads = await services().forge(branch.project).threads(branch.number)
    return [thread for thread in threads if not thread.resolved]


# Where a round finds nothing to read. A branch with rounds behind it has the
# work of those rounds sitting in the worktree, and that goes to the gate
# whatever the forge says about the rest; a branch nothing touched is left as
# it was, and nothing is committed or labelled on it.
def _no_more(branch: Branch, note: str) -> Transition:
    emit_delta(f"{branch.name}: {note}")
    if branch.answered:
        return goto(gates, Landing(branch=branch))
    return goto(pick, branch.rowed("nothing", note))


# Read the next batch of open threads into a triage.
@step
async def read(branch: Branch) -> Transition:
    # Read after the checkout, and again after every round: an item is
    # triaged against the code as it stands, and a thread the last round
    # settled is no longer open.
    try:
        threads = await _unsettled(branch)
    except ForgeError as error:
        return _stopped(branch, str(error))
    if not threads:
        return _no_more(branch, "nothing is left open")
    batch = threads[: branch.batch]
    if len(batch) < len(threads):
        emit_delta(
            f"{branch.name}: {len(threads)} threads open, reading {len(batch)} of them"
        )
    prompt = services().prompts.triage_read(branch.number, batch)
    found = (
        await services()
        .agent(branch.project)
        .ask_for(prompt, output=TriageNotes, role="reader", attended=True)
    )
    if isinstance(found, Fallen | Misread):
        return _stopped(branch, found.reason)
    # `pick` only got here on an unsettled thread, so an empty reading is the
    # reading disagreeing with the forge rather than a branch with nothing to
    # do.
    if not found.items:
        return _no_more(
            branch, "the reading found nothing, but the forge says otherwise"
        )
    return goto(plan, Triage(branch=branch, items=found.items))


# Put the triage on your terminal and take your answer to each item.
@step
async def plan(triage: Triage) -> Transition:
    report = services().report
    emit_delta("\n".join(report.triage(triage.items)))
    told: list[str] = []
    for number, item in enumerate(triage.items, start=1):
        # Free text and not a choice: an item is answered by saying how the
        # thing is supposed to work, which no four options carry. An empty
        # answer agrees with the reading's own proposal.
        said = await decide(f"{report.shown(number, item)}\n->", free=True)
        told.append(said or f"{item.action} it, as the reading says")
    prompt = services().prompts.triage_work(triage.branch.number, triage.items, told)
    threads = [item.thread for item in triage.items]
    return goto(work, Instructed(branch=triage.branch, prompt=prompt, threads=threads))


# The agent edits code and drafts every reply; it reaches the forge for
# nothing, so what it hands back is posted by the step after this one.
@step
async def work(instructed: Instructed) -> Transition:
    branch = instructed.branch
    # The checkpoint goes on before the agent, not after: this is where the
    # branch starts changing, and a cast that dies here should leave the
    # branch wearing `started`.
    if note := await _marked(branch, "started"):
        emit_delta(f"{branch.name}: {note}")
    # Straight in, with nothing asked: the triage was answered item by item a
    # step ago, so a question here is the cast asking whether you meant what
    # you just said.
    came = (
        await services()
        .agent(branch.project)
        .ask_for(
            instructed.prompt,
            output=Answered,
            role="writer",
            key=_THREAD,
            attended=True,
        )
    )
    if isinstance(came, Fallen | Misread):
        return _stopped(branch, came.reason)
    answering = Answering(branch=branch, items=came.items, threads=instructed.threads)
    return goto(answer, answering)


# The ritual's own name, spelled once for both the steps that mark it.
async def _marked(branch: Branch, state: State) -> str:
    return await mark(
        branch.project, number=branch.number, ritual="review", state=state
    )


# An issue is opened before the reply that names it, and a thread is settled
# after the reply that answers it. A thread the agent invented is reported and
# skipped; a thread it left unanswered stays open, and the next round reads it
# again. Answers with how many threads were settled.
async def _posted(answering: Answering) -> int:
    branch = answering.branch
    forge = services().forge(branch.project)
    threads = {thread.id: thread for thread in await forge.threads(branch.number)}
    settled = 0
    for item in answering.items:
        if item.thread not in answering.threads or item.thread not in threads:
            emit_delta(f"the agent answered a thread nobody triaged: {item.thread}")
            continue
        reply = item.reply
        if item.issue is not None:
            url = await forge.issue(item.issue.title, item.issue.body)
            reply = f"{reply}\n\nFiled as {url}"
        await forge.reply(branch.number, threads[item.thread], reply)
        await forge.resolve(branch.number, threads[item.thread])
        settled += 1
    return settled


# The forge writes, in one step of their own, apart from the agent's.
# Open the issues, post the replies, settle the threads, go round again.
@step
async def answer(answering: Answering) -> Transition:
    try:
        settled = await _posted(answering)
    except ForgeError as error:
        return _stopped(answering.branch, str(error))
    # Round again rather than straight to the gate: what the forge still holds
    # open is the next batch, and `read` is what finds out there is none. A
    # round that settled nothing would read the same batch back, so it goes to
    # the gate with whatever the agent did change.
    if not settled:
        return goto(gates, Landing(branch=answering.branch))
    return goto(read, answering.branch.taken(settled))


# Run the gate, repairing it up to the bound.
@step
async def gates(landing: Landing) -> Transition:
    branch = landing.branch
    project = branch.project
    # The task that broke last time round, where the runner named one.
    gate = landing.gate or project.gate
    ran = await services().tasks(project).run(gate)
    # No memory across branches, unlike the sweeps: this cast takes one branch
    # at a time with you at the terminal, and the bound is the whole of it.
    ruling = services().repairs.ruling(
        Attempt(
            project=project,
            ran=ran,
            gate=gate,
            whole=project.gate,
            spent=landing.spent(gates.name),
            bound=branch.bound,
        )
    )
    if isinstance(ruling, Fixed):
        # A task passing on its own is the reason to spend the gate, not the
        # gate passing. What lands the branch is the whole chain going green.
        if not ruling.whole:
            return goto(gates, landing.but(gate=""))
        return goto(land, branch)
    # The repair work is in the worktree and uncommitted, so there is no
    # moving on to the next branch from here.
    if isinstance(ruling, Stalled):
        return _stopped(branch, ruling.reason)
    # Another agent attempt is normally yours to approve; here the triage was
    # the approval, and the bound is what holds the loop.
    fallen = (
        await services()
        .agent(project)
        .ask(ruling.asking, role="writer", key=_THREAD, attended=True)
    )
    if fallen:
        return _stopped(branch, fallen.reason)
    return goto(gates, landing.but(gate=ruling.next_gate).charged(gates.name))


@step
async def land(branch: Branch) -> Transition:
    scm = services().scm(branch.project)
    try:
        await scm.commit("chore: act on the review triage")
        await scm.push(branch.name)
    except ScmError as error:
        return _stopped(branch, str(error))
    return goto(settle, branch)


# The one place the branch is marked done, and it is a claim about the
# threads: asked of the forge rather than assumed off the round that just ran.
# Not fatal either way: the branch is shipped whatever the count says.
# Mark the branch done where the forge says nothing is left open.
@step
async def settle(branch: Branch) -> Transition:
    left = await _open_threads(branch)
    if left is None:
        note = "the forge would not say what is left open"
    elif left:
        note = f"{left} review threads are still open"
    else:
        note = await _marked(branch, "done")
    if note:
        emit_delta(f"{branch.name}: {note}")
    return goto(pick, branch.rowed("shipped", note))


# Every ending comes here, so the report is owed however the cast ends — the
# same bargain the sweeps make, and the reason nothing between `queue_up` and
# `settle` raises: a step that gives up writes its reason into `stopped` and
# routes, and the failing is done here, after the report has been said.
# Say what each branch came to, and fail the cast where one stopped it.
@step
def recap(picking: Picking) -> Transition:
    emit_delta(services().report.review(picking))
    if picking.stopped:
        raise RitualError(picking.stopped)
    return done(picking)
